from rest_framework import fields


class HiddenContextField(fields.ChoiceField):

    def __init__(self, **kwargs):

        self.initial_only = True # The templates are customised to do fancy things when seeing this flag.
        if 'choices' in kwargs:
            super().__init__(**kwargs)
        else:
            super().__init__(choices=[], **kwargs)



# The field that requires initial. When getting initial supports looking at the context.
# TODO: Currently reusing this for Update view.
#  Would it be better if just links rather than dropdowns, and use partial update?
class HiddenInitialContextField(HiddenContextField):

    def __init__(self, **kwargs):
        assert 'initial' in kwargs, 'initial is a required argument for %s.' % self.__class__.__name__
        super().__init__(**kwargs)

    def get_initial(self):
        if callable(self.initial):
            if hasattr(self.initial, 'set_context'):
                self.initial.set_context(self)
            ret = self.initial()
            self.allow_blank = not ret
            # Filter choices here. Bad but see how can it be done better. # TODO
            # self.choices = self.choices.filter(id=)
        else:
            ret = self.initial
        if ret:
            self.choices = [ret]
        return ret
