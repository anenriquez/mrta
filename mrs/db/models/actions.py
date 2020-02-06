from fmlib.models.actions import GoTo as Action
from fmlib.utils.messages import Document
from mrs.db.models.task import InterTimepointConstraint
from pymodm import fields


class GoTo(Action):
    task_id = fields.UUIDField()
    estimated_duration = fields.EmbeddedDocumentField(InterTimepointConstraint)

    def __str__(self):
        return "id: {}, type: {}, duration: {}".format(self.action_id, self.type, self.estimated_duration)

    def get_node_names(self):
        if self.type == "ROBOT-TO-PICKUP":
            return "start", "pickup"
        elif self.type == "PICKUP-TO-DELIVERY":
            return "pickup", "delivery"

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        document["estimated_duration"] = InterTimepointConstraint.from_payload(document.pop("estimated_duration"))
        return cls.from_document(document)

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        dict_repr["estimated_duration"] = self.estimated_duration.to_dict()
        return dict_repr
