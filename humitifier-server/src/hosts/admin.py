from django.contrib import admin

from hosts.models import DataSource, Host, OperatingSystem, Scan


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    pass


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    pass


@admin.register(OperatingSystem)
class OperatingSystemAdmin(admin.ModelAdmin):
    list_display = ("name", "outdated")
    list_filter = ("outdated",)


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    pass
