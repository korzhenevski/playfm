from fabric.api import env, local, run, prefix

env.project = '/var/www/playfm'
env.virtualenv = env.project + '/venv'

def vagrant():
    # change from the default user to 'vagrant'
    env.user = 'vagrant'
    # connect to the port-forwarded ssh
    env.hosts = ['10.0.0.3']
 
    # use vagrant ssh key
    result = local('vagrant ssh-config | grep IdentityFile', capture=True)
    env.key_filename = result.split()[1]
 
def init():
	run('virtualenv {}'.format(env.virtualenv))
	#with prefix('source {}/bin/activate'.format(env.virtualenv)):
	#	run('pip install -r {}/requirements.txt'.format(env.project))
		
