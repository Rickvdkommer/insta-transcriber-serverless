import json
import tempfile
from pathlib import Path
from csv_profile_transcriber import CSVProfileTranscriber

def handler(event):
    """
    RunPod serverless handler for Instagram transcription requests.
    Expects event['input'] to contain the same JSON as the /transcribe POST endpoint.
    """
    try:
        request_data = event.get('input', {})
        if not request_data.get('posts'):
            return {"success": False, "error": "No posts provided"}

        # Create a temporary CSV file in /tmp
        temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, dir='/tmp', encoding='utf-8')
        csv_path = Path(temp_csv.name)
        
        import csv
        fieldnames = ['Profile', 'Reel', 'Views', 'Likes', 'Comments']
        writer = csv.DictWriter(temp_csv, fieldnames=fieldnames)
        writer.writeheader()
        profile_name = request_data.get('profile_name', 'unknown')
        for post in request_data.get('posts', []):
            writer.writerow({
                'Profile': profile_name,
                'Reel': post.get('url', ''),
                'Views': post.get('views', 0),
                'Likes': post.get('likes', 0),
                'Comments': post.get('comments', 0)
            })
        temp_csv.close()

        # Run the transcriber
        transcriber = CSVProfileTranscriber("extension_transcriptions")
        result_file = transcriber.process_csv_file(
            csv_file=str(csv_path),
            top_count=request_data.get('top_count', 5),
            sort_by=request_data.get('sort_by', 'view_count'),
            filter_pinned=False,
            profile_name=profile_name,
            quick_transcribe=request_data.get('quick_transcribe', False)
        )

        # Read the combined transcription (if created)
        output_text = None
        filename = None
        if result_file and Path(result_file).exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                output_text = f.read()
            filename = Path(result_file).name
        else:
            # fallback filename
            filename = f"{profile_name}_transcription.txt"

        # Clean up temp CSV
        try:
            csv_path.unlink()
        except Exception:
            pass

        return {
            "success": True,
            "output_file": str(result_file),
            "output_text": output_text,
            "filename": filename,
            "profile_name": profile_name,
            "message": "Transcription completed successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)} 