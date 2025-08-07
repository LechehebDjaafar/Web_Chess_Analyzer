# session_manager.py - إدارة البيانات خارج الجلسة

import json
import time
import os
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, storage_dir="temp_analysis"):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # تنظيف البيانات القديمة عند البدء
        self.cleanup_old_files()
    
    def save_analysis(self, analysis_data):
        """حفظ بيانات التحليل في ملف مؤقت"""
        try:
            analysis_id = f"{analysis_data['username']}_{int(time.time())}"
            file_path = os.path.join(self.storage_dir, f"{analysis_id}.json")
            
            # إضافة timestamp للملف
            analysis_data['created_at'] = time.time()
            analysis_data['analysis_id'] = analysis_id
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Analysis saved to file: {analysis_id}")
            return analysis_id
            
        except Exception as e:
            print(f"❌ Error saving analysis: {e}")
            return None
    
    def load_analysis(self, analysis_id):
        """تحميل بيانات التحليل من الملف"""
        try:
            file_path = os.path.join(self.storage_dir, f"{analysis_id}.json")
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            # التحقق من انتهاء صلاحية البيانات (4 ساعات)
            if time.time() - analysis_data.get('created_at', 0) > 14400:  # 4 ساعات
                self.delete_analysis(analysis_id)
                return None
            
            return analysis_data
            
        except Exception as e:
            print(f"❌ Error loading analysis: {e}")
            return None
    
    def delete_analysis(self, analysis_id):
        """حذف بيانات التحليل"""
        try:
            file_path = os.path.join(self.storage_dir, f"{analysis_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted analysis: {analysis_id}")
        except Exception as e:
            print(f"❌ Error deleting analysis: {e}")
    
    def cleanup_old_files(self):
        """تنظيف الملفات القديمة (أكثر من 4 ساعات)"""
        try:
            current_time = time.time()
            deleted_count = 0
            
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    file_age = current_time - os.path.getctime(file_path)
                    
                    if file_age > 14400:  # 4 ساعات
                        os.remove(file_path)
                        deleted_count += 1
            
            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} old analysis files")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

# إنشاء مثيل عام
session_manager = SessionManager()
