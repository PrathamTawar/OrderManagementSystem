from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .base_view import CustomerAPIView
from .models import Customer, CustomerType
from .serializers import (
    CustomerCreateUpdateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerTypeCreateUpdateSerializer,
    CustomerTypeDetailSerializer,
    CustomerTypeListSerializer,
)


class CustomerListCreateView(CustomerAPIView):
    model = Customer
    serializer_class = CustomerListSerializer
    create_serializer_class = CustomerCreateUpdateSerializer
    permission_map = {  # noqa: RUF012
        "GET": "customers.view_customer",
        "POST": "customers.add_customer",
    }

    def get(self, request):
        customers = self.get_queryset()
        serializer = self.get_serializer(customers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={"membership": request.org_membership},
        )
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(self.serializer_class(customer).data, status=201)


class CustomerDetailView(CustomerAPIView):
    model = Customer
    serializer_class = CustomerDetailSerializer
    create_serializer_class = CustomerCreateUpdateSerializer
    update_serializer_class = create_serializer_class
    permission_map = {  # noqa: RUF012
        "GET": "customers.view_customer",
        "PUT": "customers.edit_customer",
        "DELETE": "customers.delete_customer",
    }

    def get(self, request, pk):
        customer = self.get_object(pk=pk)
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    def put(self, request, pk):
        customer = self.get_object(pk=pk)
        serializer = self.get_serializer(
            customer,
            data=request.data,
            partial=True,
            context={"membership": request.org_membership},
        )
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(self.serializer_class(customer).data, status=200)

    def delete(self, request, pk):
        customer = self.get_object(pk=pk)
        customer.delete()
        return Response(status=204)


class CustomerTypeListCreateView(CustomerAPIView):
    model = CustomerType
    serializer_class = CustomerTypeListSerializer
    create_serializer_class = CustomerTypeCreateUpdateSerializer
    permission_map = {  # noqa: RUF012
        "GET": "customers.view_customertype",
        "POST": "customers.add_customertype",
    }

    def get(self, request):
        customer_types = self.get_queryset()
        serializer = self.get_serializer(customer_types, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={"membership": request.org_membership},
        )
        serializer.is_valid(raise_exception=True)
        customer_type = serializer.save()
        return Response(self.serializer_class(customer_type).data, status=201)


class CustomerTypeDetailView(CustomerAPIView):
    model = CustomerType
    serializer_class = CustomerTypeDetailSerializer
    create_serializer_class = CustomerTypeCreateUpdateSerializer
    update_serializer_class = create_serializer_class
    permission_map = {  # noqa: RUF012
        "GET": "customers.view_customertype",
        "PUT": "customers.edit_customertype",
        "DELETE": "customers.delete_customertype",
    }

    def get(self, request, pk):
        customer_type = self.get_object(pk=pk)
        serializer = self.get_serializer(customer_type)
        return Response(serializer.data)

    def put(self, request, pk):
        customer_type = self.get_object(pk=pk)
        serializer = self.get_serializer(
            customer_type,
            data=request.data,
            partial=True,
            context={"membership": request.org_membership},
        )
        serializer.is_valid(raise_exception=True)
        customer_type = serializer.save()
        return Response(self.serializer_class(customer_type).data, status=200)

    def delete(self, request, pk):
        customer_type = self.get_object(pk=pk)
        customer_type.delete()


class Health(APIView):
    permission_classes = [AllowAny]  # noqa: RUF012

    def get(self, request):
        return Response({"status": "ok"})
