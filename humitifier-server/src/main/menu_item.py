from simple_menu import MenuItem


class HumitifierMenuItem(MenuItem):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child_selected = False

    def process(self, request):
        super().process(request)

        if any([child.selected or child.child_selected for child in self.children]):
            self.child_selected = True
