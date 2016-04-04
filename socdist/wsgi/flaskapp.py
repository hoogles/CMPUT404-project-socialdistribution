import flask
from flask import Flask, request, render_template
import json
import sqlite3
import os.path
from werkzeug import secure_filename
from flask.ext.cors import CORS
import CommonMark
import urllib2

app = Flask(__name__)
CORS(app)
root = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(root,'uploads/')
app.debug = True

parser = CommonMark.Parser()

logged=False
user = "None"


####################################
#Sub-routines
####################################

#check if a user is in their friends list returns True if they are or false if they arent
def isFriend(user, person):
	#user = str(request.cookies.get('user'))
	user = user.split('@')[0]
	person = person.split('@')[0]
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS '+user+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
	conn.commit()
	sql = "SELECT * FROM "+user+" WHERE friend="+person
	c.execute(sql)
	friend = c.fetchone()
	conn.close()
	return (friend!=None)

#returns true if person is a friend of a friend
def isFriendofaFriend(person):
	user = str(request.cookies.get('user')).split('@')[0]
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	sql = "SELECT * FROM "+user
	c.execute('CREATE TABLE IF NOT EXISTS '+user+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
	conn.commit()
	c.execute(sql)	
	friends = c.fetchall()
	for friend in friends:
		if isFriend(friend, person):
			return True
	conn.close()
	return False

def get_follows(user):
	user = user.split('@')[0]
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS '+user+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
	conn.commit()
	sql = "SELECT * FROM "+user
	c.execute(sql)	
	f = c.fetchall()
	conn.close()
	return f

def get_friends():
	user = str(request.cookies.get('user')).split('@')[0]
	friends = []
	follows = get_follows(user)
	for f in follows:
		f =f.split('@')[0]
		if isFriend(f, user):
			friends.append(f)
	return friends



#returns friends of friends 
def FsOfFs():
	user = request.cookies.get('user').split('@')[0]
	user=str(user)
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS '+user+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
	conn.commit()
	sql = "SELECT * FROM "+user
	c.execute(sql)	
	friends = c.fetchall()
	FsOfAllFs = []
	for friend in friends:
		friend = str(friend[0])
		if friend == "None":
			return FsOfAllFs
		sql = "SELECT * FROM "+friend
		c.execute(sql)
		FF = c.fetchall()
		for fof in FF:
			FsOfAllFs.append(str(fof[0]))
	conn.close()
	return FsOfAllFs
	

#takes messages and marks them down
def parse_html(html):
	cm =  parser.parse(html)	
	renderer = CommonMark.HtmlRenderer()
	CommonMark.dumpAST(cm)
	cm_html = renderer.render(cm)
	return cm_html

#reverse a list ######################################
def reverse(l):
	reversed_list = [0]*len(l)
	i = len(l)-1
	j=0
	while i>=0:
		reversed_list[j] = l[i]
		i-=1
		j+=1
	return reversed_list


#gets the stream reads all then puts it in the db
def poll_github_init():
	user = str(request.cookies.get('user'))
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS '+user.split('@')[0]+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
	conn.commit()

	c.execute("SELECT git FROM users WHERE user_name=\'"+user+'\'')

	git_acct = str(c.fetchone()[0])
	git_stream = None
	git_url = "https://github.com/"+git_acct+".atom"
	try:
		git_stream = urllib2.urlopen(git_url)
	except:
		conn.close()
		return 
	stream = git_stream.readlines()
	ident = "<title type=\"html\">"	
	for line in stream:
		if ident in line:
			text = line[23:-9]
			c.execute('SELECT ID FROM posts ORDER BY ID')	
			id_num = int(c.fetchall()[-1][0])+1
			priv = str(0)
			try:
				c.execute('INSERT INTO posts (ID, content,post_date,poster,privacy) VALUES ('+str(id_num)+',\''+text+'\', CURRENT_TIMESTAMP, \''+str(user)+'\','+priv+')')
				conn.commit()
			except Exception, e:
				conn.close()
				return "error="+str(e)	
	conn.close()
	

#gets the stream reads it and write the stream to the posts
def poll_github():
	user = str(request.cookies.get('user'))
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS '+user.split('@')[0]+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
	conn.commit()

	c.execute("SELECT git FROM users WHERE user_name=\'"+user+'\'')

	git_acct = str(c.fetchone()[0])
	git_stream = None
	git_url = "https://github.com/"+git_acct+".atom"
	try:
		git_stream = urllib2.urlopen(git_url)
	except:
		conn.close()
		return 
	stream = git_stream.readlines()
	ident = "<title type=\"html\">"	
	published = "<published>"
	sql= ""
	c.execute("SELECT post_date FROM posts ORDER BY ID")
	date = str(c.fetchall()[-1][0])
	for line in stream:
		published_time = ""
		if ident in line:
			text = line[23:-9]
			c.execute('SELECT ID FROM posts ORDER BY ID')	
			id_num = int(c.fetchall()[-1][0])+1
			priv = str(0)
			sql = 'INSERT INTO posts (ID, content,post_date,poster,privacy) VALUES ('+str(id_num)+',\''+text+'\', CURRENT_TIMESTAMP, \''+str(user)+'\','+priv+')'
			
		if published in line:
			published_time = line[16:-12] 
		if published_time > date and sql!= "":
			try:
				c.execute(sql)
				conn.commit()
				published_time = ""
				sql=""
			except Exception, e:
				conn.close()
				return "error="+str(e)	
	conn.close()

#####################################
#Main functions
######################################
@app.route('/')
def hello():
	#you gotta log in
	user = str(request.cookies.get('user'))
	if user== "admin@socdist":
		return render_template('admin.html')
	elif user!="None":
		return render_template('index.html')
	else:
		return render_template('login.html')

######################################
@app.route('/signup', methods=['GET', 'POST','PUT'])
def signup():
	poll_github_init()
	if request.method == 'POST' or request.method == 'PUT':
		conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
		c = conn.cursor()
		username = str(request.form['user'])
		password = str(request.form['pass'])
		git = str(request.form['git'])
		try: 
			img = request.files['profile_image']	
			img_name = str(secure_filename(img.filename))
		except:
			if  bool(request.files['profile_image'])==False:
				img_name = "default.jpg"
		uname = str(request.form['pass'])
		try:
			c.execute('INSERT INTO users (user_name, password,profile_pic,uname,git) VALUES (\''+username+'\',\''+password+'\',\''+img_name+'\',\''+uname+'\',\''+git+'\')')
			user = username.split('@')
			c.execute('CREATE TABLE IF NOT EXISTS '+user[0]+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
			conn.commit()
		except Exception, e:
			conn.close()
			return render_template('signup.html')
		conn.close()	
	elif request.method == 'GET':
		return render_template('signup.html')
	return render_template('login.html')


#Log in to server ##############################
@app.route('/login', methods=['GET', 'POST'])
def login():
	user = request.cookies.get('user')
	username = str(request.form['user'])

	try:
		conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
		c = conn.cursor()
		if request.method=='POST':
			#open db
			try:
				c.execute('SELECT * FROM users WHERE user_name=\''+username+'\'')
				info = c.fetchone()
				true_pass = str(info[1])
				user_pass = request.form['pass']
				if true_pass == user_pass:
					logged = True
					if username == "admin@socdist":
						cookie = flask.make_response(render_template("admin.html"))
					else:
						cookie = flask.make_response(render_template("index.html"))
					cookie.set_cookie('user',username)
					return cookie
				else:
					conn.close()			
					return render_template('login.html')
			except:
				return render_template('login.html')
		conn.close()
		logged = True
		#user = request.form['user']
		#return str(user)
		if username == "admin@socdist":
			return render_template('admin.html')
		else:
			return render_template('index.html')
	except:
		return render_template('login.html')

######################################
@app.route('/logout', methods=['POST'])
def logout():
	try:
		cookie = flask.make_response(render_template("login.html"))
		user = None
		cookie.set_cookie('user','',expires=0)	
		return render_template('login.html')
	except Exception, e:
		return str(e)

# Update the stream #####################################
@app.route('/update', methods=['GET'])
def update():
	poll_github()
	user = request.cookies.get('user')
	if user=="None":
		return render_template('login.html')
	try:
		posts ={}
		if request.method=="GET":
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			c.execute('CREATE TABLE IF NOT EXISTS '+user.split('@')[0]+'(friend varchar(255),friend_request varchar(255),img_name varchar(255), priv int)')
			conn.commit()
			c.execute('SELECT * FROM posts ORDER BY ID')
			posts = {}
			count=0
			post_content = c.fetchall()
			post_content = reverse(post_content)
			fofs = FsOfFs()
			for post in post_content:
				post_p = list(post)
				poster = post[4]
				post_p[1] = parse_html(str(post_p[1]))
				if (poster in fofs) or poster==user:
					posts[count]=tuple(post_p)				
					count+=1		
			conn.close()
		return flask.jsonify(posts)
	except Exception, e:
		return str(e)

######################################
@app.route('/<username>',methods=['GET'])
def user_page(username):
	#you gotta log in
	user = str(request.cookies.get('user'))
	if user!="None":
		return render_template('user.html')
	else:
		return render_template('login.html')

######################################
@app.route('/get_user/<username>',methods=['GET'])
def get_user_infos(username):
	user = request.cookies.get('user')
	try:
		posts ={}
		if request.method=="GET":
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			c.execute('SELECT * FROM posts WHERE poster=\''+user+'\' ORDER BY ID')
			posts = {}
			count=0
			post_content = c.fetchall()
			post_content = reverse(post_content)
			for post in post_content:
				posts[count]=post				
				count+=1		
			conn.close()
		return flask.jsonify(posts)
	except Exception, e:
		return str(e) 
	
######################################
@app.route('/get_user_info/<username>',methods=['GET'])
def get_user_info(username):
	try:
		info ={}
		if request.method=="GET":
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			c.execute('SELECT * FROM users WHERE user_name=\''+username+'\'')
			info[0] = c.fetchall()		
			conn.close()
		return flask.jsonify(info)
	except Exception, e:
		return str(e) 
	
######################################
@app.route('/images/<image>', methods=['GET'])
def give_image(image):
	try:
		user = request.cookies.get('user')
		conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
		c = conn.cursor()
		sql = "SELECT poster FROM images WHERE img_name=\'"+image+"\'"
		c.execute(sql)
		poster = str(c.fetchone()[0])
		sql = "SELECT priv FROM "+poster+"WHERE img_name=\'"+image+"\'"
		c.execute(sql)
		priv = int(c.fetchone()[0])
		allowed = ((priv==0) or (poster==user) or (isFriends(user,poster) and (priv==1)))
		if (request.method=='GET') and (allowed==true):
			path = 'uploads'
			return flask.send_file(os.path.join(path, image),mimetype="image/*")
	except Exception, e:
		return str(e)

######################################
''' Upload posts to the database'''
@app.route('/upload',methods=['POST','PUT'])
def upload():
	user = request.cookies.get('user')
	try:
		if request.method =="POST" or request.method =="PUT":
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			if request.files['post_image']:	
				text = parse_html(str(request.form['post_text']))
				img = request.files['post_image']	
				c.execute('SELECT ID FROM posts ORDER BY ID')
				id_num = int(c.fetchall()[-1][0])+1
				img_name = str(secure_filename(img.filename))
				priv = str(request.form['privacy'])
				try:
					img.save(app.config['UPLOAD_FOLDER']+str(img_name))
					c.execute('INSERT INTO posts (ID, content, file_name,post_date,poster,privacy) VALUES ('+str(id_num)+',\''+str(text)+'\', \''+str(img_name)+'\', CURRENT_TIMESTAMP, \''+str(user)+'\','+privacy+')')
					conn.commit()
					c.execute('INSERT INTO' + user.split('@') +'(img_name,priv) VALUES (\''+img_name+'\',\''+priv+'\')')
					conn.commit()
				except Exception, e:
					conn.close()
					return "error..="+str(e)
				return flask.redirect('/')
			
			else:
			#No image
				text = str(request.form['post_text'])
				c.execute('SELECT ID FROM posts ORDER BY ID')	
				id_num = int(c.fetchall()[-1][0])+1
				priv = str(request.form['privacy'])
				try:
					c.execute('INSERT INTO posts (ID, content,post_date,poster,privacy) VALUES ('+str(id_num)+',\''+text+'\', CURRENT_TIMESTAMP, \''+str(user)+'\','+priv+')')
					conn.commit()
				except Exception, e:
					conn.close()
					return "error="+str(e)
	except Exception, y:
		return str(y)
	conn.close()	
	return flask.redirect('/')

######################################
''' Upload comments to the database'''
@app.route('/upload_comment/<pid>',methods=['POST','PUT'])
def upload_comment(pid):
	user = request.cookies.get('user')
	pid = str(pid)
	try:
		if request.method =="POST" or request.method =="PUT":
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			if request.files['post_image_comment'+pid]:	
				text = parse_html(str(request.form['post_text_comment'+pid]))
				img = request.files['post_image_comment'+pid]	
				c.execute('SELECT ID FROM posts ORDER BY ID')
				id_num = int(c.fetchall()[-1][0])+1
				img_name = str(secure_filename(img.filename))
				try:
					img.save(app.config['UPLOAD_FOLDER']+str(img_name))
					c.execute('INSERT INTO posts (ID, content, file_name,post_date,poster,privacy,iscommentof) VALUES ('+str(id_num)+',\''+str(text)+'\', \''+str(img_name)+'\', CURRENT_TIMESTAMP, \''+str(user)+'\',1,'+pid+')')
					conn.commit()
					c.execute('INSERT INTO' + user.split('@') +'(img_name,priv) VALUES (\''+img_name+'\',1)')
					conn.commit()
				except Exception, e:
					conn.close()
					return "error..="+str(e)
				return flask.redirect('/')
			
			else:
				text = parse_html(str(request.form['post_text_comment'+pid]))
				c.execute('SELECT ID FROM posts ORDER BY ID')	
				id_num = int(c.fetchall()[-1][0])+1
				try:
					c.execute('INSERT INTO posts (ID, content,post_date,poster,privacy,iscommentof) VALUES ('+str(id_num)+',\''+text+'\', CURRENT_TIMESTAMP, \''+str(user)+'\',1,'+pid+')')
					conn.commit()
				except Exception, e:
					conn.close()
					return "error="+str(e)
	except Exception, y:
		return str(y)
	conn.close()	
	return flask.redirect('/')

######################################
@app.route('/edit_user')
def edit_user():
	try:
		user = request.cookies.get('user')
		if user!="None":
			return render_template('edit.html')
		else:
			return render_template('login.html')
	except Exception, e:
		return str(e)

######################################
@app.route('/edit_user_info', methods=['POST', 'PUT'])
def edit_user_info():
	user = request.cookies.get('user')
	try:
		if request.method =="POST" or request.method =="PUT":
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			email = request.form['user_email']
			img = request.files['user_image']
			uname = request.form['username']
			upass = request.form['user_pass']
			git = request.form['git']
			sql = "UPDATE users SET "
			if email:
				sql += "user_name=\'"+str(email)+"\',"
			if img:
				img_name = str(secure_filename(img.filename))
				sql += "profile_pic=\'"+str(img_name)+"\',"
				try:
					img.save(app.config['UPLOAD_FOLDER']+str(img_name))
					
				except Exception, e:
					conn.close()
					return "error..="+str(e)
			if uname:
				sql += "uname=\'"+str(uname)+"\',"
			if upass:
				sql += "user_name=\'"+str(upass)+"\',"
			if git:
				sql += "git=\'"+str(git)+"\',"		
			if sql[-1] == ',':
				sql = sql[0:-1]
			sql += " WHERE user_name=\'"+user+"\'"
			c.execute(sql)
			conn.commit()
			if git():
				poll_github_init()
	except Exception, y:
		return str(y)
	conn.close()	
	return flask.redirect('/'+user)

######################################
@app.route('/get_friends',methods=['POST','PUT'])
def get_friends():
	user = request.cookies.get('user')
	if request.method == "GET":
		try:
			friends_d ={}
			user = request.cookies.get('user')
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			c.execute('CREATE TABLE IF NOT EXISTS '+user[0]+'(friend varchar(255))')
			conn.commit()
			sql = "SELECT friend FROM \'" + user+'\''
			c.execute(sql)
			friends = c.fetchall()
			c.close()
			conn.close()
			count=0
			for friend in friends:
				friends[count] = friend
				count+=1
			return flask.jsonify(friends_d)
		except Exception, e:
			return str(e)

######################################
@app.route('/befriend/<friend>')
def befriend(friend):
	#try:
	user = request.cookies.get('user')
	user = user.split('@')[0]
	friend = friend.split('@')[0]
	conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
	c = conn.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS '+user+'(friend varchar(255),friend_request varchar(255))')
	conn.commit()
	friend = friend.split('@')[0]
	sql = "INSERT INTO "+user+"(friend) VALUES (\'"+friend+"\')"
	c.execute(sql)
	conn.commit()
	sql = "SELECT friend_request FROM "+friend+" WHERE friend_request=\'"+user+"\'"
	c.execute(sql)
	conn.commit()
	x = c.fetchall()
	if x:
		sql="DROP INDEX "+user+" ON " +friend
		c.execute(sql)
		conn.commit()
		sql = "INSERT INTO "+friend+"(friend) VALUES (\'"+user+"\')"
		c.execute(sql)
		conn.commit()
	else:
		sql = "INSERT INTO "+friend+"(friend_request) VALUES (\'"+user+"\')"
		c.execute(sql)
		conn.commit()
	c.close()
	conn.close()
	return flask.redirect('/')

######################################
@app.route('/unfriend/<friend>')
def unfriend(friend):
	try:
		user = request.cookies.get('user')
		conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
		c = conn.cursor()
		c.execute('CREATE TABLE IF NOT EXISTS '+user[0]+'(friend varchar(255))')
		conn.commit()
		user = user.split('@')[0]
		friend = friend.split('@')[0]
		sql ="DELETE FROM \""+user+"\"WHERE friend=\""+friend+"\""
		c.execute(sql)
		conn.commit()
		c.close()
		conn.close()
		return flask.redirect('/')
	except Exception, e:
		return str(e)

######################################
@app.route('/delete/<post>')
def delete_post(post):
	try:
		user = request.cookies.get('user')
		conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
		c = conn.cursor()
		sql = "DELETE FROM posts WHERE ID="+str(post)
		c.execute(sql)
		conn.commit()
		c.close()
		conn.close()
		return flask.redirect('/')
	except Exception, e:
		return str(e)

######################################
@app.route('/get_users', methods=['GET'])
def get_users():
	user = request.cookies.get('user')
	if request.method == "GET":
		try:
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			sql = "SELECT user_name FROM users"
			c.execute(sql)
			users_sql = c.fetchall()
			c.close()
			conn.close()
			users = {}
			count=0
			for u in users_sql:
				if u!=user:
					users[count]=u				
					count+=1		
			conn.close()
			return flask.jsonify(users)
		except Exception, e:
			return str(e)

######################################
@app.route('/find_friends',methods=['GET'])
def find_friends():
	try:
		user = request.cookies.get('user')
		if user!="None":
			return render_template('users.html')
		else:
			return render_template('login.html')
	except Exception, e:
		return str(e)

######################################
@app.route('/del_user/<u>')
def del_user(u):
	user = request.cookies.get('user').split('@')[0]
	if user=="admin@socdist":
		conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
		c = conn.cursor()
		sql = "DROP TABLE "+u
		c.execute(sql)
		sql = "DELETE FROM users WHERE user_name=\'"+u+"\'"
		conn.commit()
		c.close()
		conn.close()
		return render_template("admin.html")
	else:
		return flask.redirect("http://socdist-lab6lramsey.rhcloud.com")

######################################
@app.route('/get_freqs',methods=['GET'])
def get_freqs():
	if request.method=='GET':
		try:
			user = request.cookies.get('user').split('@')[0]
			sql = "SELECT friend_request FROM" + user	
			conn = sqlite3.connect(os.path.dirname(__file__)+'/../db.sqlite3')
			c = conn.cursor()
			c.execute(sql)
			freqs = {}
			freqs_sql = c.fetchall()
			i = 0
			for req in freqs_sql:
				freqs[i] = req
				i+=1
			conn.close()
			return flask.jsonify(freqs)
	
		except:
			return render_template("login.html")	

######################################
@app.route('/find_friend_request')
def find_friend_request():
	try:
		user = request.cookies.get('user')
		if user!="None":
			return render_template('freqs.html')
		else:
			return render_template('login.html')
	except Exception, e:
		return str(e)

if __name__ == '__main__':
	app.run()
