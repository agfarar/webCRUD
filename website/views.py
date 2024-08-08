from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from flask_login import login_required, current_user
from .models import Product
from . import db
import os
from werkzeug.utils import secure_filename
import json
import pandas as pd
from io import BytesIO

views = Blueprint('views', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        delete_product_id = request.form.get('deleteProduct')
        if delete_product_id:
            product = Product.query.get(delete_product_id)
            if product and product.user_id == current_user.id:
                db.session.delete(product)
                db.session.commit()
                flash('Product deleted!', category='success')
            else:
                flash('Product not found or unauthorized access.', category='error')
        else:
            # Handle product addition
            name = request.form.get('name')
            description = request.form.get('description')
            code = request.form.get('code')
            image = request.files.get('image')

            if not name or not code:
                flash('Product name and code are required!', category='error')
            else:
                existing_product = Product.query.filter_by(code=code).first()
                if existing_product:
                    flash('Product code already exists! Please use a different code.', category='error')
                else:
                    filename = None
                    if image and allowed_file(image.filename):
                        filename = secure_filename(image.filename)
                        image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    else:
                        filename = 'default.jpg'
                        flash('No image uploaded or invalid image format. Using default image.', category='warning')

                    new_product = Product(name=name, description=description, code=code, image=filename, user_id=current_user.id)
                    db.session.add(new_product)
                    db.session.commit()
                    flash('Product added!', category='success')

    products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template("home.html", user=current_user, products=products)

@views.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.user_id != current_user.id:
        flash('You are not authorized to edit this product.', category='error')
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        code = request.form.get('code')
        image = request.files.get('image')

        if not name or not code:
            flash('Product name and code are required!', category='error')
        else:
            product.name = name
            product.description = description
            product.code = code

            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                product.image = filename

            db.session.commit()
            flash('Product updated successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template('edit_product.html', product=product, user=current_user)



@views.route('/delete-product', methods=['POST'])
@login_required
def delete_product():
    try:
        product_data = json.loads(request.data)
        product_id = product_data.get('productId')
        if not product_id:
            print("No product ID provided.")
            return jsonify({"error": "No product ID provided"}), 400
        
        print(f"Received product ID to delete: {product_id}")
        product = Product.query.get(product_id)

        if product and product.user_id == current_user.id:
            db.session.delete(product)
            db.session.commit()
            print("Product deleted successfully!")
            return jsonify({"success": "Product deleted"}), 200
        else:
            print("Product not found or unauthorized access.")
            return jsonify({"error": "Product not found or unauthorized access"}), 404
    except Exception as e:
        print(f"Error deleting product: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

@views.route('/download-products', methods=['GET'])
@login_required
def download_products():
    products = Product.query.all()
    data = {
        'ID': [p.id for p in products],
        'Name': [p.name for p in products],
        'Description': [p.description for p in products],
        'Code': [p.code for p in products],
        'Image': [p.image for p in products],
        'User ID': [p.user_id for p in products]
    }
    
    df = pd.DataFrame(data)
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')

    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name='products.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
