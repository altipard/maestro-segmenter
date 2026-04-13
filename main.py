import re
import grpc

from concurrent import futures
from grpc_reflection.v1alpha import reflection

from semantic_text_splitter import MarkdownSplitter, TextSplitter

import segmenter_pb2
import segmenter_pb2_grpc

class SegmenterServicer(segmenter_pb2_grpc.SegmenterServicer):
    def Segment(self, request: segmenter_pb2.SegmentRequest, context: grpc.aio.ServicerContext):
        file = request.file

        text = file.content.decode('utf-8') if file.content else ""

        capacity = request.segment_length if request.segment_length > 0 else 1000
        overlap = request.segment_overlap if request.segment_overlap > 0 else 0

        if is_markdown(text):
            splitter = MarkdownSplitter(capacity, overlap)
            chunks = splitter.chunks(text)
        else:
            splitter = TextSplitter(capacity, overlap)
            chunks = splitter.chunks(text)

        segments = [segmenter_pb2.Segment(text=chunk) for chunk in chunks]
        return segmenter_pb2.SegmentResponse(segments=segments)

def is_markdown(text):
    patterns = [
        r'^#{1,6}\s',                    # Headings
        r'\*\*[^*]+\*\*',                # Bold with **
        r'__[^_]+__',                    # Bold with __
        r'\*[^*]+\*',                    # Italic with *
        r'_[^_]+_',                      # Italic with _
        r'\[.+?\]\(.+?\)',               # Links
        r'!\[.+?\]\(.+?\)',              # Images
        r'^\s*[-\*\+]\s+',               # Unordered lists
        r'^\s*\d+\.\s+',                 # Ordered lists
        r'^>\s+',                        # Blockquotes
        r'`{1,3}[^`]+`{1,3}',            # Inline code or code blocks
        r'^\s*---+\s*$',                 # Horizontal rules
    ]

    return bool(re.search('|'.join(patterns), text, flags=re.MULTILINE))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    segmenter = SegmenterServicer()
    segmenter_pb2_grpc.add_SegmenterServicer_to_server(segmenter, server)

    SERVICE_NAMES = (
        segmenter_pb2.DESCRIPTOR.services_by_name['Segmenter'].full_name,
        reflection.SERVICE_NAME,
    )

    reflection.enable_server_reflection(SERVICE_NAMES, server)

    server.add_insecure_port('[::]:50051')
    server.start()

    print("Maestro Segmenter started. Listening on port 50051.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
