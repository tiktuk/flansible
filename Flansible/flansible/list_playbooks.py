import os
from flask_restful import Resource, Api
from flask_restful_swagger import swagger
from flansible import app
from flansible import api, app, celery, playbook_root, auth
from flansible import verify_password, get_inventory_access
from ModelClasses import AnsibleCommandModel, AnsiblePlaybookModel, AnsibleRequestResultModel, AnsibleExtraArgsModel
from jinja2 import Environment, meta

import celery_runner


class Playbooks(Resource):
    @swagger.operation(
        notes='List ansible playbooks. Configure search root in config.ini',
        nickname='listplaybooks',
        responseMessages=[
            {
              "code": 200,
              "message": "List of playbooks"
            }
          ]
    )
    @auth.login_required
    def get(self):
        yamlfiles = []
        print("listing playbooks in " + playbook_root)
        for root, dirs, files in os.walk(playbook_root):
            for name in files:
                if name.endswith((".yaml", ".yml")):
                    fileobj = {'playbook': name, 'playbook_dir': root}
                    yamlfiles.append(fileobj)
        
        env = Environment()
        returnedfiles = []
        
        for fileobj in yamlfiles:
            if 'group_vars' in fileobj['playbook_dir']:
                pass
            elif fileobj['playbook_dir'].endswith('handlers'):
                pass
            elif fileobj['playbook_dir'].endswith('vars'):
                pass
            else:
                # Parse the playbook for variables
                playbook_filename = '%s/%s' % (fileobj['playbook_dir'], fileobj['playbook'])
                playbook_text = open(playbook_filename).read()
                ast = env.parse(playbook_text)
                playbook_variables = list(meta.find_undeclared_variables(ast))
                fileobj.update(variables=playbook_variables)
                
                returnedfiles.append(fileobj)
        
        return returnedfiles


api.add_resource(Playbooks, '/api/listplaybooks')
