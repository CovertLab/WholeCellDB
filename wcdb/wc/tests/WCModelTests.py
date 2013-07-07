from django.test import TestCase

from wc.models.models import Parameter, Option, Process
from wc.models.stateproperty import StateProperty
from wc.models.wcmodel import WCModel



class WCModelTests(TestCase):
    def test_create_empty_model(self):
        WCModel.objects.create(name="Test WCModel", organism="Test organism")
        self.assertQuerysetEqual(
                WCModel.objects.all(),
                ['<WCModel: Test WCModel, Test organism>'])

    # Add things through the methods.
    def test_add_parameter_method(self):
        WCModel.objects.create(name="Test WCModel", organism="Test organism")
        test_model = WCModel.objects.get(pk=1)
        test_model.parameters.add(
                Parameter.objects.create(name="Parameter A"))

    def test_add_option_method(self):
        WCModel.objects.create(name="Test WCModel", organism="Test organism")
        test_model = WCModel.objects.get(pk=1)
        test_model.options.add(
                Option.objects.create(name="Test Option"))

    def test_add_process_method(self):
        WCModel.objects.create(name="Test WCModel", organism="Test organism")
        test_model = WCModel.objects.get(pk=1)
        test_model.processes.add(
                Process.objects.create(name="Test Process"))

    def test_add_stateproperty_method(self):
        WCModel.objects.create(name="Test WCModel", organism="Test organism")
        test_model = WCModel.objects.get(pk=1)
        test_model.state_properties.add(
                StateProperty.objects.create(
                    state_name="State A",
                    property_name="Property a"))

    def test_state_method(self):
        WCModel.objects.create(name="Test WCModel", organism="Test organism")
        test_model = WCModel.objects.get(pk=1)
        test_model.state_properties.add(
            StateProperty.objects.create(
                state_name="State A",
                property_name="Property a"),
            StateProperty.objects.create(
                state_name="State B",
                property_name="Property b"))
        self.assertQuerysetEqual(
                test_model.state('State A'),
                ['<StateProperty: State A - Property a>'])