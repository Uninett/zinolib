from typing import ClassVar

from pydantic import BaseModel

from . import tcl, toml
from .models import UserConfig, OptionalUserConfig, ServerV1Config, Options


def _parse_tcl(config_dict, section):
    fixed_dict = tcl.normalize(config_dict)
    connection = fixed_dict["connections"][section]
    options = fixed_dict["global_options"]
    connection['password'] = connection.pop("secret")
    connection['port'] = int(connection.pop("port"))
    return connection, options


class ZinoV1Config(ServerV1Config, Options):
    """
    How to use::

    Given a legacy tcl config file stored on disk, containing at minimum server,
    username and secret::

        > config = ZinoV1Config.from_tcl()

    With a toml-file stored on disk, which needs only a server::

        > config = ZinoV1Config.from_toml()

    Explicitly set the user and Zino1 secret::

        > config.set_userauth(username, secret)

    Read some command-line arguments via argparse.ArgumentParser and update the
    config::

        > config.update_from_args(args)
    """
    DEFAULT_SECTION: ClassVar = "default"

    @classmethod
    def get_legacy_class(cls):
        return type("ZinoV1LegacyConfig", (UserConfig, cls), dict())

    @classmethod
    def get_class(cls):
        return type("ZinoV1Config", (OptionalUserConfig, cls), dict())

    @classmethod
    def from_dict(cls, config_dict, section=DEFAULT_SECTION):
        connection = config_dict["connections"][section]
        options = config_dict.get("options", {})
        classobj = cls.get_class()
        return classobj(**connection, **options)

    @classmethod
    def from_tcl(cls, filename=None, section=DEFAULT_SECTION):
        config_dict = tcl.parse_tcl_config(filename)
        connection, options = _parse_tcl(config_dict, section)
        classobj = cls.get_legacy_class()
        return classobj(**connection, **options)

    @classmethod
    def from_toml(cls, filename=None, section=DEFAULT_SECTION):
        config_dict = toml.parse_toml_config(filename)
        return cls.from_dict(config_dict)

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
