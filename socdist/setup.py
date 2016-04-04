from setuptools import setup

setup(name='django on Red Hat Openshift',
    version='1.3.3',
    description='django on OpenShift',
    author='',
    author_email='',
    STATIC_URL = '/static/',
    STATIC_ROOT = PROJECT_PATH + '/static/',
)
