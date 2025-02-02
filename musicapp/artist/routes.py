from flask import render_template, request, Blueprint, url_for, abort, flash, redirect
from flask_login import current_user, login_required
from musicapp.models import Song, Artist_info, Like
from musicapp.songs.forms import SearchForm
from musicapp import db
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from musicapp.artist.forms import ArtistForm
from musicapp.artist.utils import save_image
import os
from flask import current_app as app

artists = Blueprint('artists', __name__)


@artists.context_processor
def layout():
    form = SearchForm()
    return dict(form=form)



@artists.route('/artist')
@login_required
def artist():
    page = request.args.get('page', 1, type=int)
    artists = Artist_info.query.paginate(page=page, per_page=12)
    return render_template('artist.html', title='All Artists', artists=artists)


@artists.route('/artist/<int:artist_id>')
@login_required
def artist_info(artist_id):
    artist = Artist_info.query.get_or_404(artist_id)
    artist_songs = Song.query.filter_by(artist_id=artist_id).all()
    if artist.image:
        artist_image = url_for('static', filename='artist_images/' + artist.image)
    else:
        artist_image = url_for('static', filename='artist_images/default.png')
    num_songs = len(artist_songs)
    total_likes = 0
    for song in artist_songs:
        total_likes += db.session.query(func.count(Like.user_id)).filter_by(song_id=song.id).scalar()
    return render_template('artist_info.html', title=artist.name, artist=artist, artist_songs=artist_songs, artist_image=artist_image, num_songs=num_songs, total_likes=total_likes, current_user=current_user)


@artists.route('/artist/<int:artist_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist_info.query.get_or_404(artist_id)
    if current_user.is_admin == False and current_user.is_manager == False:
        abort(403) 
        
    if form.validate_on_submit():
        artist.name = form.name.data
        artist.birth_date = form.birth_date.data
        # Delete old image if new image is uploaded
        if form.image.data:
            if artist.image and artist.image != 'default.png':
                os.remove(os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], artist.image))
            image_file = save_image(form.image.data)
            artist.image = image_file
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            return render_template('errors/500.html', error=e), 500
        flash('Artist has been updated!', 'success')
        return redirect(url_for('artists.artist_info', artist_id=artist.id))
    elif request.method == 'GET':
        form.name.data = artist.name
        form.birth_date.data = artist.birth_date
    return render_template('edit_artist.html', title='Edit Artist', form=form, artist=artist, current_user=current_user)


def delete_artist(artist_id):
    # Check if total songs is 1 (the song being deleted)
    artist = Artist_info.query.get_or_404(artist_id)
    artist_songs = Song.query.filter_by(artist_id=artist_id).all()
    if len(artist_songs) > 1:
        return False
    
    # Delete artist image if it exists
    if artist.image and artist.image != 'default.png':
        os.remove(os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], artist.image))

    db.session.delete(artist)
    db.session.commit()
    return True