from app import app, db, Achievement

with app.app_context():
    Achievement.query.delete()
    db.session.commit()
    print("تم حذف جميع الإنجازات بنجاح") 