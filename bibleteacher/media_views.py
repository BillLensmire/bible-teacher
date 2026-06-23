import os
import mimetypes
from django.http import HttpResponse, Http404
from django.conf import settings


def media_view(request, path):
    """Serve media files with HTTP Range request support for audio/video seeking."""
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise Http404('File not found')
    
    file_size = os.path.getsize(full_path)
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    range_header = request.headers.get('Range', '')
    
    if range_header:
        # Parse Range header: "bytes=0-1023" or "bytes=0-"
        try:
            range_spec = range_header.strip().split('=')[1]
            start_str, end_str = range_spec.split('-')
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        except (ValueError, IndexError):
            start, end = 0, file_size - 1
        
        end = min(end, file_size - 1)
        content_length = end - start + 1
        
        with open(full_path, 'rb') as f:
            f.seek(start)
            data = f.read(content_length)
        
        response = HttpResponse(data, status=206, content_type=content_type)
        response['Content-Length'] = str(content_length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        return response
    
    # No range header - serve full file
    with open(full_path, 'rb') as f:
        data = f.read()
    
    response = HttpResponse(data, content_type=content_type)
    response['Content-Length'] = str(file_size)
    response['Accept-Ranges'] = 'bytes'
    return response
