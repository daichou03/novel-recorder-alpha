from rest_framework.renderers import TemplateHTMLRenderer

# Not working and not being used, just let it sit there.
class InitialTemplateHTMLRenderer(TemplateHTMLRenderer):

    def serializer_to_form_fields(self, serializer):

        fields  = super(InitialTemplateHTMLRenderer, self).serializer_to_form_fields(serializer)
        initial = serializer.context.get('form_initial')

        if initial:

            for field_name, field in fields.items():

                if field_name in initial: field.initial = initial[field_name]

        return fields
