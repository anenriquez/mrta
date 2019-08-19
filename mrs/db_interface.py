import logging

from mrs.structs.timetable import Timetable


class DBInterface(object):
    def __init__(self, ccu_store):
        self.ccu_store = ccu_store

    def add_task(self, task):
        """Saves the given task to a database as a new document under the "tasks" collection.
        """
        collection = self.ccu_store.db['tasks']
        dict_task = task.to_dict()
        self.ccu_store.unique_insert(collection, dict_task, 'id', task.id)

    def update_task(self, task):
        """ Updates the given task under the "tasks" collection
        """
        collection = self.ccu_store.db['tasks']
        task_dict = task.to_dict()

        found_dict = collection.find_one({'id': task_dict['id']})

        if found_dict is None:
            collection.insert(task_dict)
        else:
            collection.replace_one({'id': task.id}, task_dict)

    def get_tasks(self):
        """ Returns a dictionary with the tasks in the "tasks" collection

        """
        collection = self.ccu_store.db['tasks']
        tasks_dict = dict()
        for task in collection.find():
            tasks_dict[task['id']] = task
        return tasks_dict

    def remove_task(self, task_id):
        """ Removes task with task_id from the collection "tasks"
        """
        collection = self.ccu_store.db['tasks']
        collection.delete_one({'id': task_id})

    def update_task_status(self, task, status):
        task.status.status = status
        logging.debug("Updating task status to %s", task.status.status)
        self.update_task(task)

    def get_task(self, task_id):
        """Returns a task dictionary representing the task with the given id.
        """
        collection = self.ccu_store.db['tasks']
        task_dict = collection.find_one({'id': task_id})
        return task_dict

    def add_timetable(self, timetable):
        """
        Saves the given timetable under the "timetables" collection
        """
        collection = self.ccu_store.db['timetables']
        robot_id = timetable.robot_id
        timetable_dict = timetable.to_dict()

        self.ccu_store.unique_insert(collection, timetable_dict, 'robot_id', robot_id)

    def update_timetable(self, timetable):
        """ Updates the given timetable under the "timetables" collection
        """
        collection = self.ccu_store.db['timetables']
        timetable_dict = timetable.to_dict()
        robot_id = timetable.robot_id

        found_dict = collection.find_one({'robot_id': robot_id})

        if found_dict is None:
            collection.insert(timetable_dict)
        else:
            collection.replace_one({'robot_id': robot_id}, timetable_dict)

    def get_timetable(self, robot_id, stp):
        collection = self.ccu_store.db['timetables']
        timetable_dict = collection.find_one({'robot_id': robot_id})

        if timetable_dict is None:
            return
        timetable = Timetable.from_dict(timetable_dict, stp)
        return timetable

