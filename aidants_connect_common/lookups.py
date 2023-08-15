from django.db.models import CharField, Lookup, TextField


@CharField.register_lookup
@TextField.register_lookup
class IsNullOrBlank(Lookup):
    lookup_name = "isnull_or_blank"
    prepare_rhs = False

    def as_sql(self, compiler, connection):
        if not isinstance(self.rhs, bool):
            raise ValueError(
                f"The QuerySet value for {self.lookup_name} "
                f"lookup must be True or False."
            )

        sql, params = compiler.compile(self.lhs)
        # sql expression par will appear 2 times in final expression so any parameters
        # will need to be formatted twice.
        params.extend(params)
        neg = "NOT " if not self.rhs else ""
        neq = "!" if not self.rhs else ""
        op = "AND" if not self.rhs else "OR"
        sql = f"({sql} IS {neg}NULL {op} TRIM({sql}) {neq}= '')"

        return sql, params
