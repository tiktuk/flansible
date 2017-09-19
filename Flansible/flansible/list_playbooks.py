import os
from flask_restful import Resource, Api
from flask_restful_swagger import swagger
from flansible import app
from flansible import api, app, celery, playbook_root, auth, global_meta
from flansible import verify_password, get_inventory_access
from ModelClasses import AnsibleCommandModel, AnsiblePlaybookModel, AnsibleRequestResultModel, AnsibleExtraArgsModel
from jinja2 import Environment, FileSystemLoader, meta

import celery_runner

from tdh_utils import playbook_as_schema, playbook_metadata


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
        
        for root, dirs, files in os.walk(playbook_root):
            for name in files:
                if name.endswith((".yaml", ".yml")):
                    fileobj = {'playbook': name, 'playbook_dir': root}
                    yamlfiles.append(fileobj)
        
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
                pls = playbook_as_schema(
                    fileobj['playbook_dir'],
                    fileobj['playbook'],
                    dict_name='USER'
                )
                
                playbook_schema = pls['schema']
                errors = pls['errors']
                
                fileobj.update(schema=playbook_schema)
                
                if errors:
                    fileobj.update(error=errors)
                
                metadata = playbook_metadata(
                    fileobj['playbook_dir'],
                    fileobj['playbook'],
                    global_meta=global_meta
                )
                
                fileobj.update(metadata=metadata)
                
                returnedfiles.append(fileobj)
        
        return returnedfiles


api.add_resource(Playbooks, '/api/listplaybooks')
