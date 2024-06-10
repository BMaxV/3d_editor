# simple 3d editor

unfortunately, I'm using a bunch of my modules. They are not on pypi and require some manual setup. This should work, let me know if it doesn't:
```
pip install requirements.txt
pip install git+https://github.com/BMaxV/my_xmlsave.git
pip install git+https://github.com/BMaxV/vector.git
pip install git+https://github.com/BMaxV/panda_object_creation.git
pip install git+https://github.com/BMaxV/panda3d_interface_glue.git
pip install git+https://github.com/BMaxV/panda3d_collisions.git
```

creates some very simple tiles in panda

left clicking spawns a marker at that location

saving, saves an xml file that you can then manually edit.

loading loads the same xml file

----------

the "load terrain" button loads an xml that was saved by the 

https://github.com/BMaxV/simple_rivers

script.
