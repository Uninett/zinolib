from pydantic import BaseModel

from . import tcl, toml
from .models import UserConfig, ServerV1Config, Options


def _parse_tcl(config_dict, section):
    fixed_dict = tcl.normalize(config_dict)
    connection = fixed_dict["connections"][section]
    options = fixed_dict["global_options"]
    connection['password'] = connection.pop("secret")
    connection['port'] = int(connection.pop("port"))
    return connection, options


class ZinoV1Config(UserConfig, ServerV1Config, Options):
    """
    How to use::

    Make a config-class from the tcl-config stored on disk::

        > config = ZinoV1Config.from_tcl()

    Get the actual user and Zino1 secret and update the config-object::

        > config.set_userauth(actual_username, secret)

    Read some command-line arguments via argparse.ArgumentParser and update the
    config::

        > config.update_from_args(args)
    """

    @classmethod
    def from_tcl(cls, filename=None, section="default"):
        config_dict = tcl.parse_tcl_config(filename)
        connection, options = _parse_tcl(config_dict, section)
        return cls(**connection, **options)

    @classmethod
    def from_toml(cls, filename=None, section="default"):
        config_dict = toml.parse_toml_config(filename)
        connection = config_dict["connections"][section]
        return cls(**connection, **config_dict["options"])

    def set_userauth(self, username, password):
        self.username = username
        self.password = password

    def update_from_args(self, args):
        """
        Assumes argparse-style args namespace object

        arg-names not found in the config-object are ignored.
        """
        for arg in vars(args):
            value = getattr(args, arg, None)
            if arg in vars(self):
                setattr(self, arg, value)
