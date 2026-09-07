import csv
import io

from flask import (
    Blueprint,
    request,
)
from flask_login import login_required
from werkzeug.wrappers.response import Response

from ..exceptions import exception_handler
from ...part_list import BrickPartList
from ...set_list import BrickSetList
from ...individual_part_list import IndividualPartList

admin_export_page = Blueprint(
    'admin_export',
    __name__,
    url_prefix='/admin/export'
)


# Export all sets to CSV
@admin_export_page.route('/sets/csv', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_sets_csv() -> Response:

    set_list = BrickSetList()
    all_sets = set_list.all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Set Number', 'Quantity', 'Includes Spares', 'Inventory Ver'])

    for set_item in all_sets.records:
        writer.writerow([
            set_item.fields.set,
            1,  # Each set instance counts as 1
            'True',  # BrickTracker tracks spares separately
            1  # Inventory version (always 1 for now)
        ])

    # Prepare response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_sets.csv'}
    )


# Export all parts to CSV
@admin_export_page.route('/parts/csv', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_parts_csv() -> Response:

    owner_id = request.args.get('owner')
    color_id = request.args.get('color')
    theme_id = request.args.get('theme')
    year = request.args.get('year')

    part_list = BrickPartList()
    part_list.all_filtered(owner_id, color_id, theme_id, year)

    part_quantities = {}
    for part in part_list.records:
        key = (part.fields.part, part.fields.color)
        if key in part_quantities:
            part_quantities[key] += part.fields.quantity
        else:
            part_quantities[key] = part.fields.quantity

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Part', 'Color', 'Quantity'])

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        writer.writerow([part_num, color_id, quantity])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_parts.csv'}
    )


# Export all parts to BrickLink XML format
@admin_export_page.route('/parts/bricklink-xml', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_parts_bricklink() -> Response:

    owner_id = request.args.get('owner')
    color_id = request.args.get('color')
    theme_id = request.args.get('theme')
    year = request.args.get('year')

    part_list = BrickPartList()
    part_list.all_filtered(owner_id, color_id, theme_id, year)

    part_quantities = {}
    for part in part_list.records:
        part_num = part.fields.bricklink_part_num or part.fields.part
        color_id = part.fields.bricklink_color_id or part.fields.color

        key = (part_num, color_id)
        if key in part_quantities:
            part_quantities[key] += part.fields.quantity
        else:
            part_quantities[key] = part.fields.quantity

    xml_lines = ['<INVENTORY>']

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        xml_lines.append(
            f'<ITEM><ITEMTYPE>P</ITEMTYPE><ITEMID>{part_num}</ITEMID>'
            f'<COLOR>{color_id}</COLOR><MINQTY>{quantity}</MINQTY></ITEM>'
        )

    xml_lines.append('</INVENTORY>')
    xml_content = ''.join(xml_lines)

    return Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_parts_bricklink.xml'}
    )


# Export missing/damaged parts to CSV
@admin_export_page.route('/problems/csv', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_problems_csv() -> Response:

    owner_id = request.args.get('owner')
    color_id = request.args.get('color')
    theme_id = request.args.get('theme')
    year = request.args.get('year')

    part_list = BrickPartList()
    part_list.problem_filtered(owner_id, color_id, theme_id, year)

    part_quantities = {}
    for part in part_list.records:
        qty = (part.fields.missing or 0) + (part.fields.damaged or 0)
        if qty > 0:
            key = (part.fields.part, part.fields.color)
            if key in part_quantities:
                part_quantities[key] += qty
            else:
                part_quantities[key] = qty

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Part', 'Color', 'Quantity'])

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        writer.writerow([part_num, color_id, quantity])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_problems.csv'}
    )


# Export missing/damaged parts to BrickLink XML format
@admin_export_page.route('/problems/bricklink-xml', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_problems_bricklink() -> Response:

    owner_id = request.args.get('owner')
    color_id = request.args.get('color')
    theme_id = request.args.get('theme')
    year = request.args.get('year')

    part_list = BrickPartList()
    part_list.problem_filtered(owner_id, color_id, theme_id, year)

    part_quantities = {}
    for part in part_list.records:
        qty = (part.fields.missing or 0) + (part.fields.damaged or 0)
        if qty > 0:
            part_num = part.fields.bricklink_part_num or part.fields.part
            color_id = part.fields.bricklink_color_id or part.fields.color

            key = (part_num, color_id)
            if key in part_quantities:
                part_quantities[key] += qty
            else:
                part_quantities[key] = qty

    xml_lines = ['<INVENTORY>']

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        xml_lines.append(
            f'<ITEM><ITEMTYPE>P</ITEMTYPE><ITEMID>{part_num}</ITEMID>'
            f'<COLOR>{color_id}</COLOR><MINQTY>{quantity}</MINQTY></ITEM>'
        )

    xml_lines.append('</INVENTORY>')
    xml_content = ''.join(xml_lines)

    return Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_problems_bricklink.xml'}
    )


# Helper function to get individual parts data
def get_individual_parts_data():
    """Get individual parts aggregated by part + color."""
    individual_part_list = IndividualPartList()
    individual_part_list.all()

    part_quantities = {}
    for part in individual_part_list.records:
        key = (part.fields.part, part.fields.color)
        if key in part_quantities:
            part_quantities[key] += part.fields.quantity
        else:
            part_quantities[key] = part.fields.quantity

    return part_quantities


# Helper function to get combined parts data (sets + individual)
def get_combined_parts_data(owner_id, color_id, theme_id, year):
    """Get both set-based and individual parts combined."""
    # Get set-based parts
    part_list = BrickPartList()
    part_list.all_filtered(owner_id, color_id, theme_id, year)

    combined_quantities = {}
    for part in part_list.records:
        key = (part.fields.part, part.fields.color)
        if key in combined_quantities:
            combined_quantities[key] += part.fields.quantity
        else:
            combined_quantities[key] = part.fields.quantity

    # Get individual parts
    individual_part_list = IndividualPartList()
    individual_part_list.all()

    for part in individual_part_list.records:
        key = (part.fields.part, part.fields.color)
        if key in combined_quantities:
            combined_quantities[key] += part.fields.quantity
        else:
            combined_quantities[key] = part.fields.quantity

    return combined_quantities


# Export individual parts only to CSV
@admin_export_page.route('/parts/individual/csv', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_parts_individual_csv() -> Response:

    part_quantities = get_individual_parts_data()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Part', 'Color', 'Quantity'])

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        writer.writerow([part_num, color_id, quantity])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_individual_parts.csv'}
    )


# Export combined parts (sets + individual) to CSV
@admin_export_page.route('/parts/combined/csv', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_parts_combined_csv() -> Response:

    owner_id = request.args.get('owner')
    color_id = request.args.get('color')
    theme_id = request.args.get('theme')
    year = request.args.get('year')

    part_quantities = get_combined_parts_data(owner_id, color_id, theme_id, year)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Part', 'Color', 'Quantity'])

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        writer.writerow([part_num, color_id, quantity])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_combined_parts.csv'}
    )


# Export individual parts only to BrickLink XML format
@admin_export_page.route('/parts/individual/bricklink-xml', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_parts_individual_bricklink() -> Response:

    individual_part_list = IndividualPartList()
    individual_part_list.all()

    part_quantities = {}
    for part in individual_part_list.records:
        part_num = part.fields.bricklink_part_num or part.fields.part
        color_id = part.fields.bricklink_color_id or part.fields.color

        key = (part_num, color_id)
        if key in part_quantities:
            part_quantities[key] += part.fields.quantity
        else:
            part_quantities[key] = part.fields.quantity

    xml_lines = ['<INVENTORY>']

    for (part_num, color_id), quantity in sorted(part_quantities.items()):
        xml_lines.append(
            f'<ITEM><ITEMTYPE>P</ITEMTYPE><ITEMID>{part_num}</ITEMID>'
            f'<COLOR>{color_id}</COLOR><MINQTY>{quantity}</MINQTY></ITEM>'
        )

    xml_lines.append('</INVENTORY>')
    xml_content = ''.join(xml_lines)

    return Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_individual_parts_bricklink.xml'}
    )


# Export combined parts (sets + individual) to BrickLink XML format
@admin_export_page.route('/parts/combined/bricklink-xml', methods=['GET'])
@login_required
@exception_handler(__file__)
def export_parts_combined_bricklink() -> Response:

    owner_id = request.args.get('owner')
    color_id = request.args.get('color')
    theme_id = request.args.get('theme')
    year = request.args.get('year')

    # Get set-based parts
    part_list = BrickPartList()
    part_list.all_filtered(owner_id, color_id, theme_id, year)

    part_quantities = {}
    for part in part_list.records:
        part_num = part.fields.bricklink_part_num or part.fields.part
        color_id_val = part.fields.bricklink_color_id or part.fields.color

        key = (part_num, color_id_val)
        if key in part_quantities:
            part_quantities[key] += part.fields.quantity
        else:
            part_quantities[key] = part.fields.quantity

    # Get individual parts
    individual_part_list = IndividualPartList()
    individual_part_list.all()

    for part in individual_part_list.records:
        part_num = part.fields.bricklink_part_num or part.fields.part
        color_id_val = part.fields.bricklink_color_id or part.fields.color

        key = (part_num, color_id_val)
        if key in part_quantities:
            part_quantities[key] += part.fields.quantity
        else:
            part_quantities[key] = part.fields.quantity

    xml_lines = ['<INVENTORY>']

    for (part_num, color_id_val), quantity in sorted(part_quantities.items()):
        xml_lines.append(
            f'<ITEM><ITEMTYPE>P</ITEMTYPE><ITEMID>{part_num}</ITEMID>'
            f'<COLOR>{color_id_val}</COLOR><MINQTY>{quantity}</MINQTY></ITEM>'
        )

    xml_lines.append('</INVENTORY>')
    xml_content = ''.join(xml_lines)

    return Response(
        xml_content,
        mimetype='application/xml',
        headers={'Content-Disposition': 'attachment;filename=bricktracker_combined_parts_bricklink.xml'}
    )
