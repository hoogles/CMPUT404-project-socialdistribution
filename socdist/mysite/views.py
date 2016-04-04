from django.views.generic import View
from django.http import HttpResponse
from django import get_version


class Index(View):

    def get(self, request, *args, **kwargs):
		user = request
		try:
			#f = open('app-root/repo/static/index.html', 'r')
 			#html = f.read()
			#f.close()
			us = str(user)
 			return HttpResponse(us)
		except Exception,e:
			return HttpResponse("error", str(e), str(user))

