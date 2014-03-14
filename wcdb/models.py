#!/usr/bin/env python
from django.db import models
from django.db.models import Max
from django.db.models.query import QuerySet
from django.contrib.auth.models import User
from helpers import is_sorted
from WholeCellDB.settings import HDF5_ROOT
import ast
import h5py
import numpy
import os
import re
import sys

property_tag = property

class ListField(models.TextField):
    __metaclass__ = models.SubfieldBase
    description = "Stores a python list"

    def __init__(self, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, (list, tuple)):
            return value

        return ast.literal_eval(value)

    def get_prep_value(self, value):
        if not value:
            return None
            
        return unicode(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

""" OPP """
class Option(models.Model):
    """ 
    Option 

    Creating Options
        Options.objects.create(name, value, simulation)
    """     
    process          = models.ForeignKey('Process', null=True, blank=True, related_name = 'options')
    state            = models.ForeignKey('State', null=True, blank=True, related_name = 'options')
    name             = models.CharField(max_length=255, db_index=True)
    value            = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    units            = models.CharField(max_length=255, null=True, blank=True)
    index            = models.IntegerField(default=0, db_index=True)
    simulation_batch = models.ForeignKey("SimulationBatch", related_name = 'options')

    def __unicode__(self):
        names = [
            self.simulation_batch.organism.name,
            self.simulation_batch.name,
            ]
        if self.state is not None:
            names.append(self.state.name)
        if self.state is not None:
            names.append(self.state.name)
        names.append(self.name)
        return ' - '.join(names)

    class Meta:
        app_label = 'wcdb'
        ordering = ['name', 'index']
        get_latest_by = 'simulation_batch__date'

class Parameter(models.Model):
    """ 
    Parameter

    Creating Parameter
        Parameter.objects.create(name, value, simulation)
    """     
    process          = models.ForeignKey('Process', null=True, blank=True, related_name='parameters')
    state            = models.ForeignKey('State', null=True, blank=True, related_name='parameters')
    name             = models.CharField(max_length=255, db_index=True)
    value            = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    units            = models.CharField(max_length=255, null=True, blank=True)
    index            = models.IntegerField(default=0, db_index=True)
    simulation_batch = models.ForeignKey("SimulationBatch", related_name='parameters')

    def __unicode__(self):
        names = [
            simulation_batch.organism.name,
            simulation_batch.name,
            ]
        if self.state is not None:
            names.append(self.state.name)
        if self.state is not None:
            names.append(self.state.name)
        names.append(self.name)
        return ' - '.join(names)

    class Meta:
        app_label='wcdb'
        ordering = ['name', 'index']
        get_latest_by = 'simulation_batch__date'


""" Process """      
class Process(models.Model):
    """ 
    Process 

    Creating Processes
        Process.objects.create(name, simulation_batch)
    """ 
    name             = models.CharField(max_length=255, db_index=True)
    simulation_batch = models.ForeignKey("SimulationBatch", related_name = 'processes')

    def __unicode__(self):
        return ' - '.join([
            self.simulation_batch.organism.name,
            self.simulation_batch.name,
            self.name
            ])
    
    class Meta:
        verbose_name_plural = 'Processes'
        app_label='wcdb'
        ordering = ['name']
        get_latest_by = 'simulation_batch__date'

""" States """   
class State(models.Model):
    """
    State

    State.objects.create(name, simulation)
        name        |   type
        --------------------------------------
        name        |   String
        simulation  |   wcdb.models.Simulation
    """
    name             = models.CharField(max_length=255, db_index=True)
    simulation_batch = models.ForeignKey('SimulationBatch', related_name='states')   
        
    # Unicode
    def __unicode__(self):
        return ' - '.join([
            self.simulation_batch.organism.name,
            self.simulation_batch.name,
            self.name
            ])
            
    class Meta:
        app_label='wcdb'
        ordering = ['name']
        get_latest_by = 'simulation_batch__date'


""" Properties """
class Property(models.Model):
    state = models.ForeignKey('State', related_name='properties')   
    name  = models.CharField(max_length=255, db_index=True)
    units = models.CharField(max_length=255, null=True, blank=True)
    
    def get_dataset_slice(self, rowLabels = None, colLabels = None, simulations = None):
        if simulations is None:
            simulations = self.state.simulation_batch.simulations.all()
            length = simulations.aggregate(Max('length'))['length__max']
        elif isinstance(simulations, Simulation):
            length = simulations.length
            simulations = [simulations]
        else:
            length = simulations[0].length
            
        sim0 = self.state.simulation_batch.simulations.all()[0]
        pv0 = sim0.property_values.get(property__id=self.id)

        shape = list(pv0.shape)
        
        if rowLabels is None:
            nRows = shape[0]
        elif isinstance(rowLabels, (QuerySet, list, tuple)):
            nRows = len(rowLabels)
        else:
            nRows = 1
            
        if colLabels is None:
            nCols = shape[0]
        elif isinstance(colLabels, (QuerySet, list, tuple)):
            nCols = len(colLabels)
        else:
            nCols = 1
        
        shape[0] = nRows
        shape[1] = nCols
        shape[2] = length
        shape.append(len(simulations))
        returnVal = numpy.empty(shape, dtype = 'float64')
        returnVal.fill(numpy.NaN)
            
        for idx, sim in enumerate(simulations):
            returnVal[:, :, :sim.length, idx] = sim.property_values.get(property=self).get_dataset_slice(rowLabels, colLabels)
            
        return returnVal
    
    def __unicode__(self):
        return ' - '.join([
            self.state.simulation_batch.organism.name,
            self.state.simulation_batch.name,
            self.state.name,
            self.name
            ])
            
    class Meta:
        app_label='wcdb'
        ordering = ['name']
        get_latest_by = 'state__simulation_batch__date'

""" Properties """
class PropertyValueManager(models.Manager):
    def create_property_value(self, simulation, property):
        """ 
        Creates a new StatePropertyValue and the associated dataset. 

        Arguments
            name            | type
            ----------------------------------
            simulation      | wcdb.models.Simulation
            property        | wcdb.models.Property 
            shape           | Tuple of Ints
            dtype           | Numpy.dtype
        """
        return self.create(simulation=simulation, property=property)

class PropertyValue(models.Model):
    """
    Property value
    """
    simulation = models.ForeignKey('Simulation', related_name='property_values')
    property   = models.ForeignKey('Property', related_name = 'values')
    shape      = ListField(null=True, blank=True)
    dtype      = models.CharField(max_length=255, null=True, blank=True)

    # Number of indices filled in in the time dimension.
    _filled = models.IntegerField(default=0) 

    objects = PropertyValueManager()
    
    @property_tag
    def path(self):
        """ The path to the dataset within the simulation h5 file """
        return "/".join([self.property.state.name,
                         self.property.name])
 
    @property_tag
    def dataset(self):
        """ The H5Py Dataset object for this property. """
        f = self.simulation.h5file
        return f[self.path]

    def set_data(self, data):
        f = self.simulation.h5file
        f.create_dataset(
            self.path,
            data = data,
            compression = "gzip",
            compression_opts = 4, 
            chunks = True)
        f.flush()
        f.close()
        
        self.shape = data.shape
        self.dtype = data.dtype.name
        self.save()
        
    def add_data(self, ts):
        """ 
        This method is for adding new time slices to the data.

        Arguments
            name        type
            ----------------------
            ts      | numpy.array


        This method requires that ts.shape be the same lengh as the
        shape as self.dataset.shape, and the last dimension of ts is less than 
        the number indices available in self.dataset.

        That is, len(ts.shape) == len(self.dataset.shape)

        For example: 
            If self.dataset.shape is (2,3,4), you must pass in a tuple of
            shape (2,3,x). 

            If ts == {{0, 1}, {2, 3}, {4, 5}} then it will fail.

            Instead, it should be ts == {{[0], [1]}, {[2], [3]}, {[4], [5]}}
        """
        # If all dimensions, except the time dimension, are equal.
        """ I'm not sure if I should be doing this if statement, or if I
            should just let it throw the exception."""
        if ts.shape[:-1] == self.dataset.shape[:-1]:
            lts = ts.shape[-1] # Length of the new slice.

            # If there isn't enough room for the time timeslice then
            # we'll expand the dataset so there is room.
            if lts > (self.dataset.shape[-1] - self._filled):
                new_length = self._filled + lts
                new_shape = self.dataset.shape[:-1] + (new_length,)
                self.dataset.resize(new_shape)
                self.simulation.length = new_length

            self.dataset[...,self._filled:self._filled+lts] = ts
            self.shape = self.dataset.shape
            self.dtype = self.dataset.dtype.name
            self.simulation.h5file.flush()
            self._filled += lts
            self.save()
        else:
            return False
            
    def get_dataset_slice(self, rowLabels = None, colLabels = None):
        if rowLabels is None and colLabels is None:
            returnVal = numpy.empty(self.shape, dtype = self.dtype)
            self.dataset.read_direct(returnVal)
        elif colLabels is None:
            if isinstance(rowLabels, (QuerySet, list, tuple)):
                rowIndices = [x.index for x in rowLabels]
            else:
                rowIndices = [rowLabels.index]
                
            shape = list(self.shape)
            shape[0] = len(rowIndices)
            returnVal = numpy.empty(shape, dtype = self.dtype)
            
            if is_sorted(rowIndices, key=lambda a, b: a < b):
                self.dataset.read_direct(returnVal, numpy.s_[rowIndices, ...])
            else:
                for new_rowIndex, old_rowIndex in enumerate(rowIndices):
                    self.dataset.read_direct(returnVal, numpy.s_[old_rowIndex, ...], numpy.s_[new_rowIndex, ...])
        elif rowLabels is None:
            if isinstance(colLabels, (QuerySet, list, tuple)):
                colIndices = [x.index for x in colLabels]
            else:
                colIndices = [colLabels.index]
                
            shape = list(self.shape)
            shape[1] = len(colIndices)
            returnVal = numpy.empty(shape, dtype = self.dtype)
            
            if is_sorted(colIndices, key=lambda a, b: a < b):
                self.dataset.read_direct(returnVal, numpy.s_[:, colIndices, ...])
            else:
                for new_colIndex, old_colIndex in enumerate(colIndices):
                    self.dataset.read_direct(returnVal, numpy.s_[:, old_colIndex, ...], numpy.s_[:, new_colIndex, ...])
        else:
            if isinstance(rowLabels, (QuerySet, list, tuple)):
                rowIndices = [x.index for x in rowLabels]
            else:
                rowIndices = [rowLabels.index]
            if isinstance(colLabels, (QuerySet, list, tuple)):
                colIndices = [x.index for x in colLabels]
            else:
                colIndices = [colLabels.index]
                
            shape = list(self.shape)
            shape[0] = len(rowIndices)
            shape[1] = len(colIndices)
            returnVal = numpy.empty(shape, dtype = self.dtype)
            
            if is_sorted(colIndices, key=lambda a, b: a < b):
                for new_rowIndex, old_rowIndex in enumerate(rowIndices):
                    self.dataset.read_direct(returnVal, numpy.s_[old_rowIndex, colIndices, ...], numpy.s_[new_rowIndex, ...])
            elif is_sorted(rowIndices, key=lambda a, b: a < b):
                for new_colIndex, old_colIndex in enumerate(colIndices):
                    self.dataset.read_direct(returnVal, numpy.s_[rowIndices, old_colIndex, ...], numpy.s_[:, new_colIndex, ...])
            else:
                for new_rowIndex, old_rowIndex in enumerate(rowIndices):
                    for new_colIndex, old_colIndex in enumerate(colIndices):
                        self.dataset.read_direct(returnVal, numpy.s_[old_rowIndex, old_colIndex, ...], numpy.s_[new_rowIndex, new_colIndex, ...])
                
        return returnVal

    # Unicode
    def __unicode__(self):
        return " - ".join([
            self.simulation.batch.organism.name, 
            self.simulation.batch.name, 
            '%d' % self.simulation.batch_index,
            self.property.state.name, 
            self.property.name
            ])

    class Meta:
        app_label='wcdb'
        ordering = ['simulation__batch_index']
        get_latest_by = 'simulation__batch__date'
        
class PropertyLabel(models.Model):
    property  = models.ForeignKey('Property', related_name='labels')  
    name      = models.CharField(max_length=255, null=True, blank=True, default=None, db_index=True)
    dimension = models.PositiveIntegerField(db_index=True)
    index     = models.PositiveIntegerField(db_index=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        app_label = 'wcdb'
        ordering = ['dimension', 'index']
        get_latest_by = 'property__simulation__batch__date'


class SimulationManager(models.Manager):
    def create_simulation(self, batch, batch_index = 1, length = None):        
        simulation = batch.simulations.create(
             batch_index = batch_index,
             length = length)

        f = simulation.h5file
        
        for state in batch.states.all():
            g = f.create_group('/states/' + state.name)
            
            for property in state.properties.all():
                pv = PropertyValue.objects.create_property_value(simulation, property)
                pv.save()

        f.flush()
        f.close() 

        return simulation

class Simulation(models.Model):
    """ 
    Simulation 

    Creation Arguments
        name                | type
        ----------------------------
        batch               | SimulationBatch
        batch_index         | Positive Integer
        states              | Dict String:Dict {"State name": PropertyDict,}
        length              | Float

        State Dict Format:
            {"State Name": 
                {"Property name": 
                    (
                      (k0, k1, ..., kn, t), 
                      dtype
                    )
                }
            }

        Where k0, ..., kn are Integers describing the shape of the property,
        and t is an Integer indicating how many time slices there will be.
    """
    # Metadata
    batch       = models.ForeignKey('SimulationBatch', related_name='simulations')  
    batch_index = models.PositiveIntegerField(default=1, db_index=True)
    length      = models.FloatField(null=True, blank=True, default=None)

    # Internal
    _file_permissions = models.CharField(max_length=3, default="a")

    objects = SimulationManager()

    """""""""""""""""""""""""""""""""""""""#
    # Methods for dealing with the H5 file.#
    """""""""""""""""""""""""""""""""""""""#
    @property_tag
    def file_path(self):
        """ The path to the HDF5 file for the Simulation """
        return os.path.join(HDF5_ROOT, '%d.h5' % self.id)

    @property_tag
    def h5file(self):
        """ The H5Py File object for the Simulation HDF5 file """
        return h5py.File(self.file_path, self._file_permissions)

    def lock_file(self):
        """
        Makes the file read only (when accessing through these models)
        """
        self._file_permissions = "r"

    # Other classes/methods
    def __unicode__(self):
        return ' - '.join([
            self.batch.organism.name, 
            self.batch.name, 
            '%d' % self.batch_index
            ])

    class Meta:
        unique_together = (('batch', 'batch_index'), )
        ordering = ['batch_index']
        get_latest_by = 'batch__date'
        app_label = 'wcdb'
        
class SimulationBatchManager(models.Manager):
    def create_simulation_batch(self, 
                          organism_name,
                          organism_version,
                          name="", 
                          description="", 
                          investigator_first="",
                          investigator_last="",
                          investigator_affiliation="",
                          investigator_email="",
                          ip='0.0.0.0',
                          date=None,
                          processes = [],
                          states = {}, 
                          options = {},
                          parameters = {}):

        organism = Organism.objects.get_or_create(name = organism_name)[0]
        organism.save()
        
        user = User.objects.get_or_create(
                first_name = investigator_first,
                last_name = investigator_last,
                email = investigator_email
                )[0]
        user.save()
        try:
            investigator = user.investigator
            investigator.affiliation = investigator_affiliation
        except Investigator.DoesNotExist:
            investigator = Investigator(
               user = user, 
               affiliation = investigator_affiliation
               )
        investigator.save()
        
        batch = organism.simulation_batches.create(
            name = name,
            description = description,
            organism_version = organism_version,
            investigator = investigator,
            ip = ip,
            date = date)
        batch.save()
        
        #processes
        for name in processes:
            process = batch.processes.create(name=name)
            process.save()
        
        #states
        for state_name, props in states.iteritems():
            state = batch.states.create(name=state_name)
            state.save()
            
            for prop_name, units_labels in props.iteritems():
                property = state.properties.create(name=prop_name, units=units_labels['units'])
                property.save()
                
                for dimension, dimension_labels in enumerate(units_labels['labels'] or []):
                    for index, label_name in enumerate(dimension_labels):
                        label = property.labels.create(name=label_name, dimension=dimension, index=index)
                        label.save()
                
        #options
        for prop_name, val in options.iteritems():
            if prop_name == 'processes' or prop_name == 'states':
                continue
            units = val['units']
            value = val['value']
            if isinstance(value, list):
                for index in range(len(value)):
                    option = batch.options.create(name = prop_name, units = units, value = value[index], index = index)
            else:
                option = batch.options.create(name = prop_name, units = units, value = value)
            option.save()
        
        for process_name, props in options['processes'].iteritems():
            process = batch.processes.get(name = process_name)
            
            for prop_name, val in props.iteritems():
                units = val['units']
                value = val['value']
                if isinstance(value, list):
                    for index in range(len(value)):
                        option = batch.options.create(process = process, name = prop_name, units = units, value = value[index], index = index)
                else:
                    option = batch.options.create(process = process, name = prop_name, units = units, value = value)
                option.save()
        
        for state_name, props in options['states'].iteritems():
            state = batch.states.get(name = state_name)
            
            for prop_name, val in props.iteritems():
                units = val['units']
                value = val['value']
                if isinstance(value, list):
                    for index in range(len(value)):
                        option = batch.options.create(state = state, name = prop_name, units = units, value = value[index], index = index)
                else:
                    option = batch.options.create(state = state, name = prop_name, units = units, value = value)
                option.save()
        
        #parameters
        for prop_name, val in parameters.iteritems():
            if prop_name == 'processes' or prop_name == 'states':
                continue
            units = val['units']
            value = val['value']
            if isinstance(value, list):
                for index in range(len(value)):
                    parameter = batch.parameters.create(name = prop_name, units = units, value = value[index], index = index)
            else:
                parameter = batch.parameters.create(name = prop_name, units = units, value = value)
            parameter.save()
        
        for process_name, props in parameters['processes'].iteritems():
            process = batch.processes.get(name = process_name)
            
            for prop_name, val in props.iteritems():  
                units = val['units']
                value = val['value']
                if isinstance(value, list):
                    for index in range(len(value)):
                        parameter = batch.parameters.create(process = process, name = prop_name, units = units, value = value[index], index = index)
                else:
                    parameter = batch.parameters.create(process = process, name = prop_name, units = units, value = value)
                parameter.save()
        
        for state_name, props in parameters['states'].iteritems():
            state = batch.states.get(name = state_name)
            
            for prop_name, val in props.iteritems():
                units = val['units']
                value = val['value']
                if isinstance(value, list):
                    for index in range(len(value)):
                        parameter = batch.parameters.create(state = state, name = prop_name, units = units, value = value[index], index = index)
                else:
                    parameter = batch.parameters.create(state = state, name = prop_name, units = units, value = value)
                parameter.save()
        
        return batch
        
class SimulationBatch(models.Model):
    organism         = models.ForeignKey('Organism', related_name = 'simulation_batches')
    organism_version = models.CharField(max_length=255, default="")
    name             = models.CharField(max_length=255, default="", db_index=True)
    description      = models.TextField(default="")
    investigator     = models.ForeignKey('Investigator', related_name = 'simulation_batches')
    ip               = models.IPAddressField(default="0.0.0.0")
    date             = models.DateTimeField(null=True, blank=True, db_index=True)
    date_added       = models.DateTimeField(auto_now=True, auto_now_add=True)
    
    objects = SimulationBatchManager()
    
    class Meta:
        verbose_name = 'Simulation batch'
        verbose_name_plural = 'Simulation batches'
        ordering = ['name']
        get_latest_by = 'date'
        app_label = 'wcdb'
        unique_together = (('organism', 'name'), )
        
class Organism(models.Model):
    name = models.CharField(max_length=255, default="", unique=True, db_index=True)

    def __unicode__(self):
        return self.name
    
    class Meta:
        app_label = 'wcdb'
        ordering = ['name']
        get_latest_by = 'simulation_batches__date'

class Investigator(models.Model):
    user        = models.OneToOneField(User)
    affiliation = models.CharField(max_length=255, default="")
    
    def __unicode__(self):
        return ('%s %s' % (self.first_name, self.last_name)).strip()       
    
    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        get_latest_by = 'simulation_batches__date'