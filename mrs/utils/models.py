from mrs.structs.allocation import TaskAnnouncement, Allocation, FinishRound
from mrs.structs.bid import Bid
from mrs.structs.timetable import Timetable
from ropod.utils.models import MessageFactoryBase


class MRSMessageFactory(MessageFactoryBase):
    def __init__(self):
        super().__init__()

        self.register_msg(TaskAnnouncement.__name__, self)
        self.register_msg(Allocation.__name__, self)
        self.register_msg(Bid.__name__, self)
        self.register_msg(FinishRound.__name__, self)
        self.register_msg(Timetable.__name__, self)

    def create_message(self, contents, recipients=[]):
        if isinstance(contents, TaskAnnouncement):
            model = 'TASK-ANNOUNCEMENT'
        elif isinstance(contents, Allocation):
            model = 'ALLOCATION'
        elif isinstance(contents, Bid):
            model = 'BID'
        elif isinstance(contents, FinishRound):
            model = 'FINISH-ROUND'
        elif isinstance(contents, Timetable):
            model = 'TIMETABLE'

        msg = self.get_header(model, recipients=recipients)
        payload = self.get_payload(contents, model.lower())
        msg.update(payload)
        return msg

