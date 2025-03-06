from simple_menu import MenuItem


class HumitifierMenuItem(MenuItem):

    def process(self, request):
        super().process(request)

        self.child_selected = False
        if any([child.selected or child.child_selected for child in self.children]):
            self.child_selected = True
