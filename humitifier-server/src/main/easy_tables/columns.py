from typing import Callable

from django.template.defaultfilters import date
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django_filters.conf import is_callable


class BaseColumn:

    def __init__(
        self,
        header: str | None = None,
        mark_safe: bool = False,
        hide_breakpoint: str | None = None,
        column_classes: list[str] | None = None,
        **kwargs,
    ):
        self.header = header
        self.mark_safe = mark_safe
        self.hide_breakpoint = hide_breakpoint
        self._column_classes = column_classes or []

        self.table = None

        self.extra = kwargs

    @property
    def column_classes(self):
        classes = self._column_classes.copy()

        if self.hide_breakpoint:
            classes.append("hidden")
            classes.append(f"{self.hide_breakpoint}:table-cell")

        return " ".join(classes)

    @property
    def header_classes(self):
        classes = []

        if self.hide_breakpoint:
            classes.append("hidden")
            classes.append(f"{self.hide_breakpoint}:table-cell")

        return " ".join(classes)

    def contribute_to_class(self, cls):
        self.table = cls

    def render(self, obj):
        raise NotImplementedError("Subclasses must implement this method")


class MethodColumn(BaseColumn):

    def __init__(
        self,
        *args,
        method_name: str,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.method_name = method_name

    def render(self, obj):
        method = getattr(self.table, self.method_name, None)

        if not method:
            return ""

        return method(obj)


class ValueColumn(BaseColumn):

    def __init__(
        self,
        *args,
        value_attr: Callable | str = None,
        default_value: str = "",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.value_attr = value_attr
        self.default_value = default_value

    def get_value(self, obj):
        if isinstance(obj, dict):
            if self.value_attr in obj:
                value = obj[self.value_attr]
            else:
                value = None
        else:
            value = getattr(obj, self.value_attr, None)

        if not value:
            return self.default_value

        if is_callable(value):
            value = value()

        return value

    def render(self, obj):
        value = self.get_value(obj)

        if self.mark_safe:
            return mark_safe(value)

        return value


class ModelValueColumn(ValueColumn):

    def get_value(self, obj):
        if hasattr(obj, f"get_{self.value_attr}_display"):
            return getattr(obj, f"get_{self.value_attr}_display")()

        return getattr(obj, self.value_attr)


class BooleanColumn(ValueColumn):

    def __init__(self, *args, yes_no_values=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.yes_no_values = yes_no_values or {
            True: "Yes",
            False: "No",
            None: "Unknown",
        }

    def render(self, obj):
        value = self.get_value(obj)

        # We don't do a direct dict lookup, as we want to handle 'truthy' and
        # 'falsy' values as well.

        if value is None:
            return self.yes_no_values[None]

        if value:
            return self.yes_no_values[True]

        return self.yes_no_values[False]


class CompoundColumn(BaseColumn):

    def __init__(
        self,
        *args,
        columns: list[BaseColumn],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.columns = columns

    def render(self, obj):
        output = [column.render(obj) for column in self.columns]
        return mark_safe(" ".join(output))


class DateColumn(ValueColumn):

    def __init__(
        self,
        *args,
        date_format: str = "Y-m-d",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.date_format = date_format

    def render(self, obj):
        value = self.get_value(obj)

        if not value:
            return ""

        return date(value, self.date_format)


class DateTimeColumn(DateColumn):

    def __init__(
        self,
        *args,
        date_format: str = "Y-m-d H:i",
        **kwargs,
    ):
        super().__init__(*args, date_format=date_format, **kwargs)


class TemplatedColumn(BaseColumn):

    def __init__(
        self,
        *args,
        template_name: str,
        context: dict | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.template_name = template_name
        self.context = context or {}

    def get_context(self, obj):
        context = self.context

        context.update(
            {
                "column": self,
                "obj": obj,
                "table": self.table,
            }
        )

        return context

    def render(self, obj):
        context = self.get_context(obj)

        return render_to_string(self.template_name, context)


class LinkColumn(TemplatedColumn):

    def __init__(
        self,
        *args,
        url: str | Callable,
        text: str | Callable,
        open_in_new_tab: bool = False,
        css_classes: str = "underline",
        **kwargs,
    ):
        if "template_name" not in kwargs:
            kwargs["template_name"] = "easy_tables/columns/link.html"

        super().__init__(*args, **kwargs)

        self.url = url
        self.text = text
        self.open_in_new_tab = open_in_new_tab
        self.css_classes = css_classes

    def get_url(self, obj):
        if is_callable(self.url):
            return self.url(obj)

        return self.url

    def get_text(self, obj):
        if is_callable(self.text):
            return self.text(obj)

        return self.text

    def get_context(self, obj):
        context = super().get_context(obj)

        context.update(
            {
                "url": self.get_url(obj),
                "text": self.get_text(obj),
                "open_in_new_tab": self.open_in_new_tab,
                "css_classes": self.css_classes,
            }
        )

        return context


class ButtonColumn(LinkColumn):

    def __init__(
        self,
        button_class: str = "btn light:btn-primary dark:btn-outline",
        show_check_function: Callable = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.css_classes = button_class
        self.show_check_function = show_check_function

    def render(self, obj):
        if self.show_check_function and not self.show_check_function(obj):
            return ""

        return super().render(obj)
