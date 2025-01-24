from flask import (
    current_app,
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
    flash
)
from flask_login import login_required
from werkzeug.wrappers.response import Response
from werkzeug.utils import secure_filename

from .exceptions import exception_handler
from ..instructions import BrickInstructions
from ..instructions_list import BrickInstructionsList
from .upload import upload_helper

instructions_page = Blueprint(
    'instructions',
    __name__,
    url_prefix='/instructions'
)


# Index
@instructions_page.route('/', methods=['GET'])
@exception_handler(__file__)
def list() -> str:
    return render_template(
        'instructions.html',
        table_collection=BrickInstructionsList().list(),
    )


# Delete an instructions file
@instructions_page.route('/<name>/delete/', methods=['GET'])
@login_required
@exception_handler(__file__)
def delete(*, name: str) -> str:
    return render_template(
        'instructions.html',
        item=BrickInstructionsList().get_file(name),
        delete=True,
        error=request.args.get('error')
    )


# Actually delete an instructions file
@instructions_page.route('/<name>/delete/', methods=['POST'])
@login_required
@exception_handler(__file__, post_redirect='instructions.delete')
def do_delete(*, name: str) -> Response:
    instruction = BrickInstructionsList().get_file(name)

    # Delete the instructions file
    instruction.delete()

    # Reload the instructions
    BrickInstructionsList(force=True)

    return redirect(url_for('instructions.list'))


# Rename an instructions file
@instructions_page.route('/<name>/rename/', methods=['GET'])
@login_required
@exception_handler(__file__)
def rename(*, name: str) -> str:
    return render_template(
        'instructions.html',
        item=BrickInstructionsList().get_file(name),
        rename=True,
        error=request.args.get('error')
    )


# Actually rename an instructions file
@instructions_page.route('/<name>/rename/', methods=['POST'])
@login_required
@exception_handler(__file__, post_redirect='instructions.rename')
def do_rename(*, name: str) -> Response:
    instruction = BrickInstructionsList().get_file(name)

    # Grab the new filename
    filename = secure_filename(request.form.get('filename', ''))

    if filename != '':
        # Delete the instructions file
        instruction.rename(filename)

        # Reload the instructions
        BrickInstructionsList(force=True)

    return redirect(url_for('instructions.list'))


# Upload an instructions file
@instructions_page.route('/upload/', methods=['GET'])
@login_required
@exception_handler(__file__)
def upload() -> str:
    return render_template(
        'instructions.html',
        upload=True,
        error=request.args.get('error')
    )


# Actually upload an instructions file
@instructions_page.route('/upload', methods=['POST'])
@login_required
@exception_handler(__file__, post_redirect='instructions.upload')
def do_upload() -> Response:
    file = upload_helper(
        'file',
        'instructions.upload',
        extensions=current_app.config['INSTRUCTIONS_ALLOWED_EXTENSIONS'],
    )

    if isinstance(file, Response):
        return file

    BrickInstructions(file.filename).upload(file)  # type: ignore

    # Reload the instructions
    BrickInstructionsList(force=True)

    return redirect(url_for('instructions.list'))


# Download instructions from Rebrickable
@instructions_page.route('/download/', methods=['GET'])
@login_required
@exception_handler(__file__)
def download() -> str:
    return render_template(
        'instructions.html',
        download=True,
        error=request.args.get('error')
    )
    
# Actually download an instructions file
@instructions_page.route('/download/', methods=['POST'])
@login_required
@exception_handler(__file__, post_redirect='instructions.download')
def do_download() -> Response:
    set_id: str = request.form.get('add-set', '')

    # BrickInstructions require an argument. Not sure which makes sense here.
    found_tags = BrickInstructions(set_id).find_instructions(set_id)
        
    return render_template('instructions.html', download=True, found_tags=found_tags)

@instructions_page.route('/confirm_download', methods=['POST'])
@login_required
@exception_handler(__file__, post_redirect='instructions.download')
def confirm_download() -> Response:
    
    # BrickInstructions require an argument. Not sure which makes sense here.
    selected_instructions = BrickInstructions("").get_list(request.form)

    if not selected_instructions:
        # No instructions selected
        return redirect(url_for('instructions.download'))

    for href, filename in selected_instructions:
        BrickInstructions(f"{filename}.pdf").download(href) 


    BrickInstructionsList(force=True)

    #flash("Selected instructions have been downloaded", 'success')
    return redirect(url_for('instructions.list'))
