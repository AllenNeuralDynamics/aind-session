# Extensions

- the core `Session` class has a minimal set of methods and attributes that are common to sessions from all platforms
- to add platform- or project-specific methods and attributes, users can register
  new namespaces: 
  - this allows for extending without subclassing ([inspired by
  Pandas](https://pandas.pydata.org/docs/development/extending.html))
  - as extensions mature they can be shipped with the core package, without
    affecting the core `Session` class
- the `ExtensionBaseClass` is provided, along with the `register_namespace`
  decorator, to make this process easier

### Example of adding a namespace

```python
# Create your custom functionality in a subclass of ExtensionBaseClass and register it with the Session class:
>>> import aind_session

>>> @aind_session.register_namespace("my_extension") # The name here is how the extension will be accessed
... class MyExtension(aind_session.ExtensionBaseClass):
...    # ...the name of the class itself is unimportant
...    
...    constant = 42
...
...    @classmethod
...    def add(cls, value) -> int:
...        return cls.constant + value
...
...    # Access the underlying Session object with self._session
...    @property
...    def oldest_data_asset_id(self) -> str:
...        return min(self._session.data_assets, key=lambda x: x.created).id

# Create a session object and access the new namespace:
>>> session = aind_session.Session("ecephys_676909_2023-12-13_13-43-40")
>>> session.my_extension.constant
42
>>> session.my_extension.add(10)
52
>>> session.my_extension.oldest_data_asset_id
'16d46411-540a-4122-b47f-8cb2a15d593a'

```

