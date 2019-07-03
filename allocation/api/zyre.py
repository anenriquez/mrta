import logging
from ropod.pyre_communicator.base_class import RopodPyre


class ZyreAPI(RopodPyre):
    def __init__(self, zyre_config):
        super().__init__(zyre_config)
        self.logger = logging.getLogger('allocation.api.zyre')
        self.callback_dict = dict()
        self.start()

    def add_callback(self, component, msg_type, callback):
        callback_funct = getattr(component, callback)
        self.__dict__[callback_funct.__name__] = callback_funct
        self.callback_dict[msg_type] = callback_funct.__name__

    def receive_msg_cb(self, msg_content):
        dict_msg = self.convert_zyre_msg_to_dict(msg_content)
        if dict_msg is None:
            return

        message_type = dict_msg['header']['type']
        self.logger.debug("Received %s message", message_type)

        callback = self.callback_dict.get(message_type, None)

        try:
            if callback is None:
                raise AttributeError
            getattr(self, callback)(dict_msg)
        except AttributeError:
            self.logger.error("No callback function found for %s messages" % message_type)
