from django.contrib import admin

from hosts.models import DataSource, Host, Scan


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    pass


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    pass


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    pass
