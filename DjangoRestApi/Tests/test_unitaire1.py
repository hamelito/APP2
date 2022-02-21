# A mettre dans le fichier tests.py de l'app Django
from django.core.urlresolvers import resolve
from django.test import TestCase
from lists.views import home
from django.template.loader import render_to_string
class StringTest(TestCase):
'''Test unitaire bidon'''
def test_concatene(self):
self.assertEqual("Bon"+"jour", "Bonjour")