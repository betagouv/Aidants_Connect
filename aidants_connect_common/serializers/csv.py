from csv import DictWriter

from django.core.serializers.python import Serializer as PythonSerializer
from django.db.models import Model


class Serializer(PythonSerializer):
    def end_object(self, obj: Model):
        dumped = self.get_dump_object(obj)
        if self.first:
            self.writer = DictWriter(
                self.stream,
                fieldnames=[
                    obj._meta.get_field(item).verbose_name
                    for item in dumped["fields"].keys()
                ],
            )
            self.writer.writeheader()

        self.writer.writerow(
            {
                obj._meta.get_field(k).verbose_name: str(v)
                for k, v in dumped["fields"].items()
            }
        )
        super().end_object(obj)

    def getvalue(self):
        # Grandparent super
        return super(PythonSerializer, self).getvalue()
