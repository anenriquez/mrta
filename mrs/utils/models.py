from ropod.utils.timestamp import TimeStamp as ts
from ropod.utils.uuid import generate_uuid
meta_model_template = 'ropod-%s-schema.json'
from mrs.structs.allocation import Tasks


class MessageFactory(object):
    # def __init__(self):
    #     self._msgs = {}
    #
    # def register_msg(self, msg_type, msg_struct):
    #     self._msgs[msg_type] = msg_struct
    #
    # def get_msg_struct(self, msg_type):
    #     msg_struct = self._msgs.get(msg_type)
    #     if not msg_struct:
    #         raise ValueError(msg_type)
    #     return msg_struct

    def create_msg(self, msg_type, contents_dict, recipients=[]):
       # msg_struct = self.get_msg_struct(msg_type)
       # msg = msg_struct(**contents)

        msg = self.get_header(msg_type, recipients=recipients)
        payload = self.get_payload(contents_dict, msg_type.lower())
        msg.update(payload)
        return msg


    @staticmethod
    def get_header(msg_type, meta_model='msg', recipients=[]):
        if recipients is not None and not isinstance(recipients, list):
            raise Exception("Recipients must be a list of strings")

        return {"header": {'type': msg_type,
                           'metamodel': 'ropod-%s-schema.json' % meta_model,
                           'msgId': generate_uuid(),
                           'timestamp': ts.get_time_stamp(),
                           'receiverIds': recipients}}

    @staticmethod
    def get_payload(contents_dict, model):
        # payload = contents.to_dict()
        metamodel = meta_model_template % model
        contents_dict.update(metamodel=metamodel)
        return {"payload": contents_dict}

