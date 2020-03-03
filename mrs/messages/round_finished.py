from mrs.utils.as_dict import AsDictMixin


class RoundFinished(AsDictMixin):
    def __init__(self, round_id):
        self.round_id = round_id

    @property
    def meta_model(self):
        return "round-finished"
