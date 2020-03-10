from fmlib.models.actions import ActionProgress as ActionProgressBase
from fmlib.models.actions import GoTo as Action
from fmlib.utils.messages import Document
from pymodm import fields

from mrs.db.models.task import InterTimepointConstraint


class GoTo(Action):
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


class ActionProgress(ActionProgressBase):
    r_start_time = fields.FloatField()
    r_finish_time = fields.FloatField()
    is_consistent = fields.BooleanField(default=True)

    class Meta:
        ignore_unknown_fields = True

    def __str__(self):
        return "action id: {}, action status: {}, start time: {}, finish time: {}".format(self.action.action_id,
                                                                                          self.status,
                                                                                          self.start_time,
                                                                                          self.finish_time)

    def update(self, status, abs_time, r_time):
        self.status = status
        if self.start_time:
            self.finish_time = abs_time
            self.r_finish_time = r_time
        else:
            self.start_time = abs_time
            self.r_start_time = r_time

    @classmethod
    def from_payload(cls, payload):
        document = Document.from_payload(payload)
        return cls.from_document(document)

    def to_dict(self):
        dict_repr = self.to_son().to_dict()
        dict_repr.pop('_cls')
        return dict_repr
