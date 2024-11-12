import copy
from collections import OrderedDict
from inspect import isclass
from typing import Iterable

from django.template.loader import render_to_string

from main.easy_tables.columns import BaseColumn, ModelValueColumn


class TableOptions:

    def __init__(self, meta):
        self.template = getattr(meta, 'template', 'easy_tables/table.html')
        self.model = getattr(meta, 'model', None)
        self.columns = getattr(meta, 'columns', [])
        self.meta = meta
        self.table = None
        self.column_type_overrides = getattr(meta, 'column_type_overrides', {})
        self.column_breakpoint_overrides = getattr(meta, 'column_breakpoint_overrides', {})
        self.no_data_message = getattr(
            meta,
            'no_data_message',
            'No data available. Please check your filters.'
        )
        self.no_data_message_wild_wasteland = getattr(
            meta,
            'no_data_message_wild_wasteland',
            "Oops! Looks like we ran out of data. Time to panic!"
        )

    def contribute_to_class(self, cls):
        self.table = cls
        columns = []

        if self.model:
            for field in self.model._meta.fields:
                if field.name in self.columns:

                    if field.name in self.column_type_overrides:
                        column = self.column_type_overrides[field.name]

                        if isclass(column):
                            instance = column(header=field.verbose_name, value_attr=field.name)
                            columns.append((field.name, instance))
                        else:
                            if column.header is None:
                                column.header = field.verbose_name

                            if hasattr(column, 'value_attr') and column.value_attr is None:
                                column.value_attr = field.name

                            columns.append((field.name, column))
                    else:
                        columns.append((field.name, ModelValueColumn(header=field.verbose_name, value_attr=field.name)))

        return columns


class DeclarativeColumnsMetaclass(type):
    def __new__(mcs, name, bases, attrs):

        # Ignore base class.
        if not bases:
            return super().__new__(mcs, name, bases, attrs)

        # Collect columns from current class and remove them from attrs.
        columns = [
            (key, value)
            for key, value in list(attrs.items())
            if isinstance(value, BaseColumn)
        ]
        for key, _ in columns:
            attrs.pop(key)

        # Create the new class.
        new_class = super().__new__(mcs, name, bases, attrs)

        # Handle Meta options
        meta = attrs.get('Meta', None)
        if meta:
            meta = TableOptions(meta)
            new_class._meta = meta
            extra_columns = meta.contribute_to_class(new_class)
            if extra_columns:
                column_keys = [column[0] for column in columns]
                for key, column in extra_columns:
                    # Do not override columns declared explicitly in the class.
                    if key not in column_keys:
                        columns.append((key, column))

        # Walk through the MRO.
        declared_columns = OrderedDict(columns)
        for base in reversed(new_class.__mro__):
            if hasattr(base, 'declared_columns'):
                declared_columns.update(base.declared_columns)
            for key, value in base.__dict__.items():
                if isinstance(value, BaseColumn):
                    declared_columns[key] = value

        # If columns are declared in the options class, reorder the columns
        # based on that order.
        if new_class._meta.columns:
            new_order = OrderedDict()
            for column_name in new_class._meta.columns:
                if column_name not in declared_columns:
                    raise ValueError(f'Column {column_name} not found in declared columns.')

                new_order[column_name] = declared_columns[column_name]

            declared_columns = new_order

        for column, bp in new_class._meta.column_breakpoint_overrides.items():
            if column in declared_columns:
                declared_columns[column].hide_breakpoint = bp

        new_class.declared_columns = declared_columns

        for column in declared_columns.values():
            column.contribute_to_class(new_class)

        return new_class


class BaseTable(metaclass=DeclarativeColumnsMetaclass):

    def __init__(
        self,
        *args,
        data: Iterable | None = None,
        paginator=None,
        page_object=None,
        ordering: str | None = None,
        ordering_fields: dict[str, str] | None =None,
        page_sizes: list[int] | None = None,
        filterset=None,
        request=None,
        **kwargs
    ):
        self.columns : dict[str, BaseColumn] = copy.deepcopy(self.declared_columns)
        self.data = data
        self.paginator = paginator
        self.page_object = page_object
        self.ordering = ordering
        self.ordering_fields = ordering_fields
        self.page_sizes = page_sizes
        self.filterset = filterset
        self.request = request

        super().__init__(*args, **kwargs)

    def render(self, obj_list = None, paginator = None):
        data = obj_list or self.data
        paginator = paginator or self.paginator

        rows = []
        for obj in data:
            row = []
            for column in self.columns.values():
                row.append((column, column.render(obj)))
            rows.append(row)

        no_data_message = self._meta.no_data_message
        if self.request and self.request.user.wild_wasteland_mode:
            no_data_message = self._meta.no_data_message_wild_wasteland

        context = {
            'table': self,
            'columns': self.columns,
            'rows': rows,
            'has_pagination': paginator is not None,
            'paginator': paginator,
            'page_obj': self.page_object,
            'page_sizes': self.page_sizes,
            'ordering': self.ordering,
            'ordering_fields': self.ordering_fields,
            'filterset': self.filterset,
            'no_data_message': no_data_message,
        }

        return render_to_string(self._meta.template, context)
