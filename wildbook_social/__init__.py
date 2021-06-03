## playgrounds + social media api's
from .Youtube.youtube import YouTube
from .iNaturalist.inaturalist import iNaturalist
from .Flickr.flickr import Flickr


## database class & visuals (geospatial and temporal)
# from .Database.database import Database
from .Database.database import Database
from .Database.visuals import Visualize
from .Database.geospatial import Geospatial

## species classification
from .SpeciesClassifier.species_classifier import SpeciesClassifier
from .SpeciesClassifier.image_data import Image

assert all((Flickr, iNaturalist, YouTube, Database, SpeciesClassifier, Image))
#assert all((Flickr, iNaturalist, YouTube, Twitter, Database_Beta))

name = "wildbook_social"