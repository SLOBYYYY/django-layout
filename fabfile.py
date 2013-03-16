from fabric.api import task, env, run, local, roles, cd, execute, hide, puts,\
    sudo
import posixpath
import re

env.project_name = '{{ project_name }}'
env.repository = 'git@github.com:SLOBYYYY/{{ project_name }}.git'
env.local_branch = 'master'
env.remote_ref = 'origin/master'
env.requirements_file = 'requirements.txt'
env.restart_command = 'supervisorctl restart {project_name}'.format(**env)
env.restart_sudo = True
env.run_django_command = '{virtualenv_dir}/bin/python manage.py {dj_command} --settings={project_conf}'
env.static_dir = '{virtualenv_dir}/var/static'
env.remote_host_command = True
env.execution_delegate = run


#==============================================================================
# Tasks which set up deployment environments
#==============================================================================

@task
def live():
    """
    Use the live deployment environment.
    """
    server = '{{ project_name }}.com'
    env.roledefs = {
        'web': [server],
        'db': [server],
    }
    env.system_users = {server: 'www-data'}
    env.virtualenv_dir = '/srv/www/{project_name}'.format(**env)
    env.project_dir = '{virtualenv_dir}/src/{project_name}'.format(**env)
    env.project_conf = '{project_name}.settings.prod'.format(**env)


@task
def dev():
    """
    Use the development deployment environment.
    """
    server = '{{ project_name }}.yourserver.com'
    env.roledefs = {
        'web': [server],
        'db': [server],
    }
    env.system_users = {server: 'www-data'}
    env.virtualenv_dir = '/srv/www/{project_name}'.format(**env)
    env.project_dir = '{virtualenv_dir}/src/{project_name}'.format(**env)
    env.project_conf = '{project_name}.settings.dev'.format(**env)


@task
def heroku():
    """
    Use heroku deployment environment.
    """
    server = '{{ project_name }}.herokuapp.com'
    env.roledefs = {
        'web': [server],
        'db': [server],
    }
    env.system_users = {server: 'www-data'}
    env.virtualenv_dir = '/app/.heroku/python'
    env.project_dir = '/app'
    env.project_conf = '{project_name}.settings.heroku'.format(**env)
    env.remote_ref = 'heroku/master'
    env.run_django_command = 'heroku run {virtualenv_dir}/bin/python manage.py {dj_command} --settings={project_conf}'
    env.remote_host_command = False
    env.static_dir = '/app/static'
    env.execution_delegate = local

# Set the default environment.
dev()


#==============================================================================
# Actual tasks
#==============================================================================

@task
@roles('web', 'db')
def bootstrap(action=''):
    """
    Bootstrap the environment.
    """
    with hide('running', 'stdout'):
        exists = env.execution_delegate('if [ -d "{virtualenv_dir}" ]; then echo 1; fi'
            .format(**env))
    if exists and not action == 'force':
        puts('Assuming {host} has already been bootstrapped since '
            '{virtualenv_dir} exists.'.format(**env))
        return
    sudo('virtualenv {virtualenv_dir}'.format(**env))
    if not exists:
        sudo('mkdir -p {0}'.format(posixpath.dirname(env.virtualenv_dir)))
        sudo('git clone {repository} {project_dir}'.format(**env))
    sudo('{virtualenv_dir}/bin/pip install -e {project_dir}'.format(**env))
    with cd(env.virtualenv_dir):
        sudo('chown -R {user} .'.format(**env))
        fix_permissions()
    requirements()
    puts('Bootstrapped {host} - database creation needs to be done manually.'
        .format(**env))


@task
@roles('web', 'db')
def push():
    """
    Push branch to the repository.
    """
    remote, dest_branch = env.remote_ref.split('/', 1)
    local('git push {remote} {local_branch}:{dest_branch}'.format(
        remote=remote, dest_branch=dest_branch, **env))


@task
def deploy(verbosity='normal'):
    """
    Full server deploy.

    Updates the repository (server-side), synchronizes the database, collects
    static files and then restarts the web service.
    """
    if verbosity == 'noisy':
        hide_args = []
    else:
        hide_args = ['running', 'stdout']
    with hide(*hide_args):
        puts('Updating repository...')
        execute(update)
        puts('Collecting static files...')
        execute(collectstatic)
        puts('Synchronizing database...')
        execute(syncdb)
        puts('Restarting web server...')
        execute(restart)


@task
@roles('web', 'db')
def update(action='check'):
    """
    Update the repository (server-side).

    By default, if the requirements file changed in the repository then the
    requirements will be updated. Use ``action='force'`` to force
    updating requirements. Anything else other than ``'check'`` will avoid
    updating requirements at all.
    """
    with cd(env.project_dir):
        remote, dest_branch = env.remote_ref.split('/', 1)
        env.execution_delegate('git fetch {remote}'.format(remote=remote,
            dest_branch=dest_branch, **env))
        with hide('running', 'stdout'):
            changed_files = env.execution_delegate('git diff-index --cached --name-only '
                '{remote_ref}'.format(**env)).splitlines()
        if not changed_files and action != 'force':
            # No changes, we can exit now.
            return
        if action == 'check':
            reqs_changed = env.requirements_file in changed_files
        else:
            reqs_changed = False
        env.execution_delegate('git merge {remote_ref}'.format(**env))
        env.execution_delegate('find -name "*.pyc" -delete')
        env.execution_delegate('git clean -df')
        fix_permissions()
    if action == 'force' or reqs_changed:
        # Not using execute() because we don't want to run multiple times for
        # each role (since this task gets run per role).
        requirements()


@task
@roles('web')
def collectstatic():
    """
    Collect static files from apps and other locations in a single location.
    """
    dj('collectstatic --link --noinput')
    with cd(env.static_dir.format(**env)):
        fix_permissions()


@task
@roles('db')
def syncdb(sync=True, migrate=True):
    """
    Synchronize the database.
    """
    dj('syncdb --noinput')


@task
@roles('web')
def restart():
    """
    Restart the web service.
    """
    if env.restart_sudo:
        cmd = sudo
    else:
        cmd = run
    cmd(env.restart_command)


@task
@roles('web', 'db')
def requirements():
    """
    Update the requirements.
    """
    env.execution_delegate('{virtualenv_dir}/bin/pip install -r {project_dir}/requirements.txt'
        .format(**env))
    with cd('{virtualenv_dir}/src'.format(**env)):
        with hide('running', 'stdout', 'stderr'):
            dirs = []
            for path in env.execution_delegate('ls -db1 -- */').splitlines():
                full_path = posixpath.normpath(posixpath.join(env.cwd, path))
                if full_path != env.project_dir:
                    dirs.append(path)
        if dirs:
            fix_permissions(' '.join(dirs))
    with cd(env.virtualenv_dir):
        with hide('running', 'stdout'):
            match = re.search(r'\d+\.\d+', env.execution_delegate('bin/python --version'))
        if match:
            with cd('lib/python{0}/site-packages'.format(match.group())):
                fix_permissions()


#==============================================================================
# Helper functions
#==============================================================================

def dj(command):
    """
    Run a Django manage.py command on the server.
    """
    command = env.run_django_command.format(dj_command=command, **env)
    env.execution_delegate(command)


def fix_permissions(path='.'):
    """
    Fix the file permissions.
    """
    if ' ' in path:
        full_path = '{path} (in {cwd})'.format(path=path, cwd=env.cwd)
    else:
        full_path = posixpath.normpath(posixpath.join(env.cwd, path))
    puts('Fixing {0} permissions'.format(full_path))
    with hide('running'):
        system_user = env.system_users.get(env.host)
        if system_user:
            env.execution_delegate('chmod -R g=rX,o= -- {0}'.format(path))
            env.execution_delegate('chgrp -R {0} -- {1}'.format(system_user, path))
        else:
            env.execution_delegate('chmod -R go= -- {0}'.format(path))
