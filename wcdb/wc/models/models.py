from django.db import models
from django.contrib.auth.models import User


""" User """
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    affiliation = models.CharField(max_length=255, 
                                   blank=True, default='')

    def __unicode__(self):
        if (self.affiliation == ""):
            return self.user.__unicode__()
        else:
            return " - ".join([self.user.__unicode__(), self.affiliation])
    
    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        get_latest_by = 'user__date_joined'
        app_label='wc'


""" Parameter """ 
class Parameter(models.Model):
    name = models.CharField(max_length=255, primary_key=True)

    def __unicode__(self):
        return self.name


    class Meta:
        app_label='wc'


class ParameterValue(models.Model):
    parameter = models.ForeignKey('Parameter')
    value = models.FloatField()

    def __unicode__(self):
        return " = ".join([self.parameter.__unicode__(), str(self.value)])


    class Meta:
        app_label='wc'


""" Option """
class Option(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


    class Meta:
        app_label='wc'


class OptionValue(models.Model):
    option = models.ForeignKey('Option')
    value = models.TextField()

    def __unicode__(self):
        return " = ".join([self.option.__unicode__(), self.value])


    class Meta:
        app_label='wc'


""" Process """
class Process(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = 'Processes'
        app_label='wc'

    def __unicode__(self):
        return self.name
