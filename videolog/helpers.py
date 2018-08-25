"""Helpers module

This module contains helper functions.
"""

def build_resource(properties):
    """Builds YouTube resource.

    Builds YouTube resource for usage with YouTube Data API. Source:
        `YouTube Data API Reference <https://developers.google.com/youtube/v3/docs/>`_.

    Args:
        properties (dict): Compact resource representation.

    Returns:
        dict: Expanded resource ready for use.
    """

    resource = {}

    for p in properties:
        # Given a key like "snippet.title", split into "snippet" and "title", where
        # "snippet" will be an object and "title" will be a property in that object.
        prop_array = p.split('.')
        ref = resource
        for pa in range(0, len(prop_array)):
            is_array = False
            key = prop_array[pa]

            # For properties that have array values, convert a name like
            # "snippet.tags[]" to snippet.tags, and set a flag to handle
            # the value as an array.
            if key[-2:] == '[]':
                key = key[0:len(key)-2:]
                is_array = True

            if pa == (len(prop_array) - 1):
                # Leave properties without values out of inserted resource.
               if properties[p]:
                   if is_array:
                       ref[key] = properties[p].split(',')
                   else:
                       ref[key] = properties[p]
            elif key not in ref:
                # For example, the property is "snippet.title", but the resource does
                # not yet have a "snippet" object. Create the snippet object here.
                # Setting "ref = ref[key]" means that in the next time through the
                # "for pa in range ..." loop, we will be setting a property in the
                # resource's "snippet" object.
                ref[key] = {}
                ref = ref[key]
            else:
                # For example, the property is "snippet.description", and the resource
                # already has a "snippet" object.
                ref = ref[key]

    return resource

def allowed_file(filename):
    """Checks uploaded file extension.

    Checks if file is allowed to upload (by its extension only). Source:
        `Flask Documentation <http://flask.pocoo.org/docs/0.12/patterns/fileuploads/>`_.

    Args:
        filename (str): File name.

    Returns:
        bool: Whether file is allowed to upload.
    """

    return not ('.' in filename and \
            filename.rsplit('.', 1)[1].lower() in set([
                'html', 'htm', 'xhtml', 'php'
            ]))
