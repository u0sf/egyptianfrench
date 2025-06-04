from app import app, db, News

with app.app_context():
    News.query.delete()
    db.session.commit()
    print("تم حذف جميع الأخبار بنجاح") 