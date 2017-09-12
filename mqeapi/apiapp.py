
from flask import Flask

from mqe import c
from mqe import util

from mqeapi import apiconfig



def create():
    if apiconfig.LOGGING_LEVEL:
        util.setup_logging(apiconfig.LOGGING_LEVEL)

    c.app = Flask(import_name=__name__)
    c.app.config.from_object(apiconfig.FlaskSettings)

    from mqeapi import appsetup

    from mqeapi import views
    c.app.register_blueprint(views.bp_api)

    from mqeweb import valdisplay
    valdisplay.setup_custom_types()

    from mqe.dao.daoregistry import register_dao_modules_from_config
    register_dao_modules_from_config(apiconfig)

    return c.app


