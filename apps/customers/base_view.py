from apps.organizations.base_view import OrgAPIView


class CustomerAPIView(OrgAPIView):
    @property
    def permission_map(self):
        if self.model is None:
            return {}

        meta = self.model._meta
        app_label = meta.app_label
        model_name = meta.model_name

        return {
            "GET": f"{app_label}.view_{model_name}",
            "HEAD": f"{app_label}.view_{model_name}",
            "POST": f"{app_label}.add_{model_name}",
            "PUT": f"{app_label}.change_{model_name}",
            "PATCH": f"{app_label}.change_{model_name}",
            "DELETE": f"{app_label}.delete_{model_name}",
        }
