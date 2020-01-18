from mrs.utils.as_dict import AsDictMixin


class Assignment(AsDictMixin):
    def __init__(self, task_id, assigned_time, node_type, is_consistent=True):
        self.task_id = task_id
        self.assigned_time = assigned_time
        self.node_type = node_type
        self.is_consistent = is_consistent

    def __str__(self):
        to_print = ""
        to_print += "Assignment (task_id: {}, assigned_time: {}, node_type: {}, " \
                    "is_consistent:{}".format(self.task_id,
                                              self.assigned_time,
                                              self.node_type,
                                              self.is_consistent)
        return to_print


class AssignmentUpdate(AsDictMixin):
    def __init__(self, robot_id, assignments):
        self.robot_id = robot_id
        self.assignments = assignments

    def to_dict(self):
        dict_repr = super().to_dict()
        assignments = list()
        for a in self.assignments:
            assignments.append(a.to_dict())
        dict_repr.update(assignments=assignments)
        return dict_repr

    @property
    def meta_model(self):
        return "assignment-update"

    @classmethod
    def to_attrs(cls, dict_repr):
        attrs = super().to_attrs(dict_repr)
        assignments = list()
        for a in attrs.get("assignments"):
            assignments.append(Assignment.from_dict(a))
        attrs.update(assignments=assignments)
        return attrs
