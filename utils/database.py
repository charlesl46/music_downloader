from peewee import Model,CharField,SqliteDatabase,AutoField,BooleanField,DateTimeField

db = SqliteDatabase("utils/database.db")

class Song(Model):
    id = AutoField(primary_key=True)
    downloaded = BooleanField(default=False)
    title = CharField(null=True)
    artist_name = CharField(null=True)
    url = CharField(null=True)
    filepath = CharField(null=True)
    cover_path = CharField(null=True)
    downloaded_on = DateTimeField(null=True)

    class Meta:
        database = db

class Settings(Model):
    id = AutoField(primary_key=True)
    set_metadata = BooleanField(default=True)
    show_history = BooleanField(default=True)

    class Meta:
        database = db