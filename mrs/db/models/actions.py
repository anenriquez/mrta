from fmlib.models.actions import GoTo as Action
from fmlib.utils.messages import Document


class GoTo(Action):

    def __str__(self):
        return "id: {}, type: {}".format(self.action_id, self.type)

    def get_node_names(self):
        if self.type == "ROBOT-TO-PICKUP":
            return "start", "pickup"
        elif self.type == "PICKUP-TO-DELIVERY":
            return "pickup", "delivery"

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        return cls.from_document(document)

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        return dict_repr
