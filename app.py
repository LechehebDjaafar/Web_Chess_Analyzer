from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import chess
import chess.pgn
import io
from datetime import datetime, timedelta
import json
import time
from collections import defaultdict, Counter
import re
import gzip
import base64
import os
import threading
import schedule

app = Flask(__name__)
app.secret_key = 'chess-analyzer-algeria-advanced-2025-ultra-secure'

# إعدادات محسنة للتطبيق
app.config.update(
    SESSION_COOKIE_SECURE=False,  # True في الإنتاج
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=4),  # 4 ساعات
    MAX_CONTENT_LENGTH=32 * 1024 * 1024,  # 32MB
    JSON_AS_ASCII=False,  # دعم النص العربي
)

# إعدادات Chess.com API
CHESS_COM_API = "https://api.chess.com/pub"
HEADERS = {
    'User-Agent': 'ChessAnalyzerAlgeria/3.1 (advanced-chess-analyzer@algeria.dz)'
}

class SessionManager:
    """إدارة البيانات خارج الجلسة لحل مشكلة حجم الكوكيز"""
    
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
            analysis_data['expires_at'] = time.time() + 14400  # 4 ساعات
            
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
                print(f"📂 Analysis file not found: {analysis_id}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            # التحقق من انتهاء صلاحية البيانات (4 ساعات)
            if time.time() > analysis_data.get('expires_at', 0):
                print(f"⏰ Analysis expired: {analysis_id}")
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
            
            if not os.path.exists(self.storage_dir):
                return
            
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    try:
                        file_age = current_time - os.path.getctime(file_path)
                        
                        if file_age > 14400:  # 4 ساعات
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        print(f"Error checking file {filename}: {e}")
                        continue
            
            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} old analysis files")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def get_storage_info(self):
        """معلومات عن التخزين"""
        try:
            if not os.path.exists(self.storage_dir):
                return {'files': 0, 'size_mb': 0}
            
            files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json')]
            total_size = 0
            
            for filename in files:
                file_path = os.path.join(self.storage_dir, filename)
                total_size += os.path.getsize(file_path)
            
            return {
                'files': len(files),
                'size_mb': round(total_size / 1024 / 1024, 2)
            }
        except Exception as e:
            print(f"Error getting storage info: {e}")
            return {'files': 0, 'size_mb': 0}

# إنشاء مثيل SessionManager عام
session_manager = SessionManager()

class AdvancedChessAnalyzer:
    def __init__(self):
        self.opening_database = self.load_opening_database()
        self.current_analysis = None
    
    def load_opening_database(self):
        """قاعدة بيانات الافتتاحيات والدفاعات المحسنة والموسعة"""
        return {
            "e4 e5": {
                "name": "اللعبة الملكية المفتوحة",
                "type": "افتتاحية",
                "category": "افتتاحيات الملك",
                "description": "افتتاحية كلاسيكية وقوية تهدف للسيطرة على المركز",
                "strength": 8.5,
                "difficulty": 6
            },
            "e4 c5": {
                "name": "الدفاع الصقلي",
                "type": "دفاع",
                "category": "دفاعات مضادة",
                "description": "دفاع عدواني ومعقد يعطي الأسود فرص هجومية",
                "strength": 9.0,
                "difficulty": 9
            },
            "d4 d5": {
                "name": "لعبة الملكة",
                "type": "افتتاحية",
                "category": "افتتاحيات الملكة",
                "description": "افتتاحية استراتيجية ومتينة تبني موضع قوي",
                "strength": 8.0,
                "difficulty": 7
            },
            "d4 Nf6": {
                "name": "الدفاع الهندي",
                "type": "دفاع",
                "category": "الدفاعات الهندية",
                "description": "دفاع مرن ومتنوع يؤخر التزام البنية المركزية",
                "strength": 7.5,
                "difficulty": 8
            },
            "e4 e6": {
                "name": "الدفاع الفرنسي",
                "type": "دفاع",
                "category": "دفاعات مغلقة",
                "description": "دفاع صلب يبني سلسلة بيادق قوية",
                "strength": 7.0,
                "difficulty": 6
            },
            "e4 c6": {
                "name": "دفاع كارو-كان",
                "type": "دفاع",
                "category": "دفاعات صلبة",
                "description": "دفاع آمن ومتين يحافظ على بنية بيادق جيدة",
                "strength": 7.2,
                "difficulty": 5
            },
            "Nf3 d5": {
                "name": "نظام ريتي",
                "type": "افتتاحية",
                "category": "الأنظمة المرنة",
                "description": "نظام مرن يطور القطع قبل تحديد البنية المركزية",
                "strength": 7.8,
                "difficulty": 7
            },
            "c4": {
                "name": "الافتتاحية الإنجليزية",
                "type": "افتتاحية",
                "category": "افتتاحيات جانبية",
                "description": "افتتاحية مرنة تسيطر على مربعات مهمة",
                "strength": 8.2,
                "difficulty": 8
            },
            "g3": {
                "name": "نظام الفيانكيتو الملكي",
                "type": "افتتاحية",
                "category": "افتتاحيات جانبية",
                "description": "نمط فيانكيتو هادئ يطور الفيل على القطر الطويل",
                "strength": 6.8,
                "difficulty": 6
            },
            "f4": {
                "name": "هجوم الملك",
                "type": "افتتاحية",
                "category": "افتتاحيات عدوانية",
                "description": "افتتاحية عدوانية تهدف للهجوم السريع على الملك",
                "strength": 6.5,
                "difficulty": 7
            },
            "d4 f5": {
                "name": "الدفاع الهولندي",
                "type": "دفاع",
                "category": "دفاعات عدوانية",
                "description": "دفاع غير تقليدي يهدف للهجوم على الجناح الملكي",
                "strength": 6.0,
                "difficulty": 8
            },
            "e4 d6": {
                "name": "دفاع بيرك",
                "type": "دفاع",
                "category": "دفاعات صلبة",
                "description": "دفاع مرن يسمح بتطور متنوع للقطع",
                "strength": 6.5,
                "difficulty": 6
            }
        }
    
    def fetch_player_info(self, username):
        """جلب معلومات اللاعب من Chess.com مع معالجة أخطاء محسنة"""
        try:
            player_url = f"{CHESS_COM_API}/player/{username}"
            response = requests.get(player_url, headers=HEADERS, timeout=20)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"Player {username} not found")
                return None
            else:
                print(f"API error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"Timeout fetching player info for {username}")
            return None
        except Exception as e:
            print(f"Error fetching player info: {e}")
            return None

    def fetch_player_stats(self, username):
        """جلب إحصائيات اللاعب من Chess.com"""
        try:
            stats_url = f"{CHESS_COM_API}/player/{username}/stats"
            response = requests.get(stats_url, headers=HEADERS, timeout=20)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return None

    def analyze_all_games_advanced(self, username, max_games=100):
        """تحليل متقدم لجميع مباريات اللاعب مع تحسينات"""
        try:
            print(f"🔍 Starting advanced analysis for {username}...")
            
            # جلب معلومات اللاعب والإحصائيات
            player_info = self.fetch_player_info(username)
            if not player_info:
                print(f"❌ Player {username} not found")
                return None
                
            player_stats = self.fetch_player_stats(username)
            
            # جلب المباريات
            print(f"📋 Fetching up to {max_games} games...")
            games = self.fetch_all_player_games(username, max_games)
            
            if not games:
                print("❌ No games found")
                return None
            
            print(f"🔬 Analyzing {len(games)} games...")
            
            # التحليل المتقدم
            advanced_analysis = self.perform_advanced_analysis(games, username)
            
            result = {
                'username': username,
                'player_info': player_info,
                'player_stats': player_stats,
                'games': games,
                'advanced_stats': advanced_analysis,
                'total_analyzed': len(games),
                'analysis_timestamp': datetime.now().isoformat(),
                'analysis_version': '3.1'
            }
            
            print(f"✅ Analysis completed successfully!")
            return result
            
        except Exception as e:
            print(f"❌ Error in advanced analysis: {e}")
            return None

    def fetch_all_player_games(self, username, max_games=50):
        """جلب جميع مباريات اللاعب مع معالجة أخطاء محسنة"""
        try:
            archives_url = f"{CHESS_COM_API}/player/{username}/games/archives"
            response = requests.get(archives_url, headers=HEADERS, timeout=20)
            
            if response.status_code != 200:
                print(f"Failed to fetch archives: {response.status_code}")
                return None
            
            archives = response.json().get('archives', [])
            if not archives:
                print("No archives found")
                return None
            
            all_games = []
            processed_games = 0
            max_archives = 6  # حد أقصى للأرشيف المعالج
            
            print(f"📦 Found {len(archives)} archives, processing latest {max_archives}...")
            
            # البدء من أحدث الأرشيف
            for i, archive_url in enumerate(reversed(archives)):
                if processed_games >= max_games or i >= max_archives:
                    break
                    
                time.sleep(0.5)  # تجنب تجاوز حدود API
                
                try:
                    print(f"⏳ Processing archive {i+1}/{min(max_archives, len(archives))}...")
                    games_response = requests.get(archive_url, headers=HEADERS, timeout=20)
                    if games_response.status_code == 200:
                        month_games = games_response.json().get('games', [])
                        
                        for game in reversed(month_games):
                            if processed_games >= max_games:
                                break
                                
                            game_analysis = self.analyze_single_game(game, username)
                            if game_analysis:
                                all_games.append(game_analysis)
                                processed_games += 1
                                
                                # طباعة التقدم كل 5 مباريات
                                if processed_games % 5 == 0:
                                    print(f"📊 Processed {processed_games}/{max_games} games...")
                                    
                except Exception as e:
                    print(f"Error processing archive {i+1}: {e}")
                    continue
            
            print(f"✅ Successfully processed {len(all_games)} games")
            return all_games
            
        except Exception as e:
            print(f"❌ Error fetching all games: {e}")
            return None

    def analyze_single_game(self, game_data, target_username):
        """تحليل مباراة واحدة مع معلومات إضافية محسنة"""
        try:
            pgn_text = game_data.get('pgn', '')
            if not pgn_text:
                return None
            
            pgn_io = io.StringIO(pgn_text)
            game = chess.pgn.read_game(pgn_io)
            
            if not game:
                return None
            
            # معلومات أساسية
            white_player = game.headers.get('White', 'Unknown')
            black_player = game.headers.get('Black', 'Unknown')
            result = game.headers.get('Result', '*')
            date = game.headers.get('Date', '')
            
            # تحديد لون اللاعب المستهدف
            player_color = 'white' if white_player.lower() == target_username.lower() else 'black'
            opponent = black_player if player_color == 'white' else white_player
            
            # تحليل النقلات المحسن
            board = game.board()
            moves = []
            move_number = 1
            
            for move in game.mainline_moves():
                move_san = board.san(move)
                move_info = {
                    'number': move_number,
                    'move': move_san,
                    'fen': board.fen(),
                    'color': 'white' if move_number % 2 == 1 else 'black',
                    'piece': str(board.piece_at(move.from_square)) if board.piece_at(move.from_square) else None,
                    'is_capture': board.is_capture(move),
                    'is_check': board.gives_check(move)
                }
                moves.append(move_info)
                board.push(move)
                move_number += 1
            
            # تحديد نتيجة اللاعب
            player_result = self.get_player_result(result, player_color)
            
            # معلومات إضافية من Chess.com
            time_control = game_data.get('time_control', 'غير محدد')
            rated = game_data.get('rated', False)
            game_url = game_data.get('url', '')
            
            # تقييم الأداء والافتتاحية
            opening = self.detect_opening_advanced(moves[:12]) if moves else "غير محدد"
            game_quality = self.evaluate_game_quality(moves, player_result)
            
            game_analysis = {
                'white_player': white_player,
                'black_player': black_player,
                'opponent': opponent,
                'player_color': player_color,
                'result': result,
                'player_result': player_result,
                'date': date,
                'time_control': time_control,
                'rated': rated,
                'url': game_url,
                'opening': opening,
                'moves': moves[:50],  # حفظ أول 50 نقلة فقط لتوفير المساحة
                'total_moves': len(moves),
                'game_duration': self.estimate_duration(moves),
                'game_quality': game_quality,
                'pgn': pgn_text[:1000] if pgn_text else ''  # اختصار PGN
            }
            
            return game_analysis
            
        except Exception as e:
            print(f"Error analyzing single game: {e}")
            return None

    def detect_opening_advanced(self, first_moves):
        """كشف الافتتاحية المتقدم مع تحليل أكثر دقة"""
        if not first_moves or len(first_moves) < 2:
            return "غير محدد"
        
        # تحليل النقلات الأولى
        moves_str = ' '.join([move['move'] for move in first_moves[:6]])
        
        # البحث في قاعدة البيانات المحسنة
        for key, opening_info in self.opening_database.items():
            if key in moves_str:
                return opening_info['name']
        
        # تحليل بناءً على النقلة الأولى
        first_move = first_moves[0]['move']
        second_move = first_moves[1]['move'] if len(first_moves) >= 2 else ''
        
        # أنماط افتتاحية متقدمة
        advanced_patterns = {
            ('e4', 'e5'): 'اللعبة الملكية المفتوحة',
            ('e4', 'c5'): 'الدفاع الصقلي',
            ('e4', 'e6'): 'الدفاع الفرنسي',
            ('e4', 'c6'): 'دفاع كارو-كان',
            ('e4', 'd6'): 'دفاع بيرك',
            ('e4', 'Nc6'): 'دفاع نيمزوفيتش',
            ('d4', 'd5'): 'لعبة الملكة',
            ('d4', 'Nf6'): 'الدفاع الهندي',
            ('d4', 'f5'): 'الدفاع الهولندي',
            ('d4', 'g6'): 'الدفاع الهندي الملكي الحديث',
            ('Nf3', 'd5'): 'نظام ريتي',
            ('Nf3', 'Nf6'): 'الافتتاحية المتناظرة',
            ('c4', 'e5'): 'الإنجليزية المعكوسة',
            ('c4', 'c5'): 'الإنجليزية المتناظرة'
        }
        
        pattern = (first_move, second_move)
        if pattern in advanced_patterns:
            return advanced_patterns[pattern]
        
        # تصنيف افتراضي محسن
        default_openings = {
            'e4': 'افتتاحية الملك',
            'd4': 'افتتاحية الملكة',
            'Nf3': 'النظام المرن',
            'c4': 'الافتتاحية الإنجليزية',
            'g3': 'نظام الفيانكيتو',
            'f4': 'هجوم الملك',
            'b3': 'نظام لارسن',
            'Nc3': 'هجوم فيينا'
        }
        
        return default_openings.get(first_move, "افتتاحية أخرى")

    def evaluate_game_quality(self, moves, result):
        """تقييم جودة المباراة"""
        if not moves:
            return 0
        
        quality_score = 5.0  # نقطة البداية
        
        # تقييم بناءً على عدد النقلات
        num_moves = len(moves)
        if 25 <= num_moves <= 60:
            quality_score += 1.0  # طول مثالي
        elif num_moves < 15:
            quality_score -= 1.5  # قصيرة جداً
        elif num_moves > 80:
            quality_score -= 0.5  # طويلة جداً
        
        # تقييم بناءً على التنوع في النقلات
        unique_pieces = set()
        for move in moves[:20]:  # أول 20 نقلة
            if move.get('piece'):
                unique_pieces.add(str(move['piece']))
        
        if len(unique_pieces) >= 4:
            quality_score += 0.5
        
        # تقييم بناءً على وجود أسر وشيكات
        captures = sum(1 for move in moves if move.get('is_capture', False))
        checks = sum(1 for move in moves if move.get('is_check', False))
        
        if captures >= 3:
            quality_score += 0.3
        if checks >= 2:
            quality_score += 0.2
        
        return min(10, max(0, round(quality_score, 1)))

    def perform_advanced_analysis(self, games, username):
        """إجراء التحليل المتقدم للمباريات مع تحسينات"""
        print("🔬 Performing advanced analysis...")
        
        analysis = {
            'openings_analysis': self.analyze_openings_advanced(games),
            'performance_by_color': self.analyze_performance_by_color(games),
            'time_control_analysis': self.analyze_time_controls(games),
            'strengths_and_weaknesses': self.identify_strengths_weaknesses_advanced(games),
            'trend_analysis': self.analyze_performance_trends(games),
            'monthly_stats': self.calculate_monthly_stats(games),
            'game_quality_analysis': self.analyze_game_quality(games),
            'opponent_analysis': self.analyze_opponents(games)
        }
        
        print("✅ Advanced analysis completed!")
        return analysis

    def analyze_openings_advanced(self, games):
        """تحليل الافتتاحيات المحسن"""
        openings_as_white = defaultdict(lambda: {
            'count': 0, 'wins': 0, 'losses': 0, 'draws': 0, 
            'avg_moves': 0, 'total_moves': 0, 'quality_sum': 0
        })
        openings_as_black = defaultdict(lambda: {
            'count': 0, 'wins': 0, 'losses': 0, 'draws': 0,
            'avg_moves': 0, 'total_moves': 0, 'quality_sum': 0
        })
        
        for game in games:
            opening_key = self.identify_opening_detailed(game['moves'])
            opening_info = self.opening_database.get(opening_key, {
                'name': game.get('opening', 'افتتاحية غير محددة'),
                'type': 'غير محدد',
                'category': 'أخرى',
                'description': 'افتتاحية غير مسجلة في قاعدة البيانات',
                'strength': 5.0,
                'difficulty': 5
            })
            
            target_dict = openings_as_white if game['player_color'] == 'white' else openings_as_black
            
            target_dict[opening_key]['count'] += 1
            target_dict[opening_key]['info'] = opening_info
            target_dict[opening_key]['total_moves'] += game.get('total_moves', 0)
            target_dict[opening_key]['quality_sum'] += game.get('game_quality', 0)
            
            if game['player_result'] == 'فوز':
                target_dict[opening_key]['wins'] += 1
            elif game['player_result'] == 'خسارة':
                target_dict[opening_key]['losses'] += 1
            else:
                target_dict[opening_key]['draws'] += 1
        
        # حساب المتوسطات والمعدلات
        for openings_dict in [openings_as_white, openings_as_black]:
            for opening_data in openings_dict.values():
                count = opening_data['count']
                if count > 0:
                    opening_data['win_rate'] = round((opening_data['wins'] / count) * 100, 1)
                    opening_data['avg_moves'] = round(opening_data['total_moves'] / count, 1)
                    opening_data['avg_quality'] = round(opening_data['quality_sum'] / count, 1)
                else:
                    opening_data['win_rate'] = 0
                    opening_data['avg_moves'] = 0
                    opening_data['avg_quality'] = 0
        
        # العثور على أفضل وأسوأ الافتتاحيات
        def get_best_worst_advanced(openings_dict):
            qualified_openings = [(k, v) for k, v in openings_dict.items() if v['count'] >= 2]
            if not qualified_openings:
                return (None, None), (None, None)
            
            best = max(qualified_openings, key=lambda x: (x[1]['win_rate'], x[1]['avg_quality']))
            worst = min(qualified_openings, key=lambda x: (x[1]['win_rate'], x[1]['avg_quality']))
            return best, worst
        
        best_as_white, worst_as_white = get_best_worst_advanced(openings_as_white)
        best_as_black, worst_as_black = get_best_worst_advanced(openings_as_black)
        
        return {
            'as_white': dict(openings_as_white),
            'as_black': dict(openings_as_black),
            'best_as_white': best_as_white,
            'worst_as_white': worst_as_white,
            'best_as_black': best_as_black,
            'worst_as_black': worst_as_black,
            'total_openings_count': len(set(list(openings_as_white.keys()) + list(openings_as_black.keys()))),
            'diversity_score': self.calculate_opening_diversity(openings_as_white, openings_as_black)
        }

    def analyze_game_quality(self, games):
        """تحليل جودة المباريات"""
        if not games:
            return {}
        
        qualities = [game.get('game_quality', 0) for game in games]
        
        return {
            'average_quality': round(sum(qualities) / len(qualities), 1),
            'high_quality_games': len([q for q in qualities if q >= 7]),
            'low_quality_games': len([q for q in qualities if q <= 4]),
            'quality_distribution': {
                'excellent': len([q for q in qualities if q >= 8]),
                'good': len([q for q in qualities if 6 <= q < 8]),
                'average': len([q for q in qualities if 4 < q < 6]),
                'poor': len([q for q in qualities if q <= 4])
            }
        }

    def analyze_opponents(self, games):
        """تحليل الخصوم"""
        opponent_stats = defaultdict(lambda: {
            'games': 0, 'wins': 0, 'losses': 0, 'draws': 0,
            'avg_game_length': 0, 'total_moves': 0
        })
        
        for game in games:
            opponent = game['opponent']
            opponent_stats[opponent]['games'] += 1
            opponent_stats[opponent]['total_moves'] += game.get('total_moves', 0)
            
            if game['player_result'] == 'فوز':
                opponent_stats[opponent]['wins'] += 1
            elif game['player_result'] == 'خسارة':
                opponent_stats[opponent]['losses'] += 1
            else:
                opponent_stats[opponent]['draws'] += 1
        
        # حساب المتوسطات
        for stats in opponent_stats.values():
            if stats['games'] > 0:
                stats['win_rate'] = round((stats['wins'] / stats['games']) * 100, 1)
                stats['avg_game_length'] = round(stats['total_moves'] / stats['games'], 1)
            else:
                stats['win_rate'] = 0
                stats['avg_game_length'] = 0
        
        # أصعب وأسهل الخصوم
        frequent_opponents = {k: v for k, v in opponent_stats.items() if v['games'] >= 2}
        
        if frequent_opponents:
            toughest = min(frequent_opponents.items(), key=lambda x: x[1]['win_rate'])
            easiest = max(frequent_opponents.items(), key=lambda x: x[1]['win_rate'])
        else:
            toughest = easiest = (None, None)
        
        return {
            'total_opponents': len(opponent_stats),
            'frequent_opponents': len(frequent_opponents),
            'toughest_opponent': toughest,
            'easiest_opponent': easiest,
            'opponent_stats': dict(list(opponent_stats.items())[:20])  # أول 20 خصم فقط
        }

    def calculate_opening_diversity(self, white_openings, black_openings):
        """حساب تنوع الافتتاحيات"""
        total_white = sum(opening['count'] for opening in white_openings.values())
        total_black = sum(opening['count'] for opening in black_openings.values())
        
        if total_white == 0 and total_black == 0:
            return 0
        
        white_diversity = len(white_openings) / max(1, total_white) * 10
        black_diversity = len(black_openings) / max(1, total_black) * 10
        
        return round((white_diversity + black_diversity) / 2, 1)

    def identify_strengths_weaknesses_advanced(self, games):
        """تحديد نقاط القوة والضعف المتقدم"""
        strengths = []
        weaknesses = []
        recommendations = []
        
        if not games:
            return {
                'strengths': ['لا توجد بيانات كافية للتحليل'],
                'weaknesses': ['يحتاج لمزيد من المباريات للتحليل الدقيق'],
                'recommendations': ['العب مباريات أكثر للحصول على تحليل شامل'],
                'game_length_analysis': {},
                'detailed_analysis': {}
            }
        
        # تحليل الأداء حسب طول المباراة
        short_games = [g for g in games if g['total_moves'] < 25]
        medium_games = [g for g in games if 25 <= g['total_moves'] < 50]
        long_games = [g for g in games if g['total_moves'] >= 50]
        
        def calculate_win_rate(game_list):
            if not game_list:
                return 0
            wins = sum(1 for g in game_list if g['player_result'] == 'فوز')
            return (wins / len(game_list)) * 100
        
        short_win_rate = calculate_win_rate(short_games)
        medium_win_rate = calculate_win_rate(medium_games)
        long_win_rate = calculate_win_rate(long_games)
        
        # تحليل نقاط القوة المتقدم
        if short_win_rate > 65 and len(short_games) >= 3:
            strengths.append("ممتاز في التكتيكات السريعة والمباريات القصيرة")
            recommendations.append("استمر في تطوير مهاراتك التكتيكية")
        
        if medium_win_rate > 60 and len(medium_games) >= 5:
            strengths.append("أداء قوي في المباريات المتوسطة الطول")
            recommendations.append("ركز على تحسين التخطيط في الوسط")
        
        if long_win_rate > 55 and len(long_games) >= 3:
            strengths.append("قدرة عالية على اللعب في النهايات")
            recommendations.append("طور معرفتك بالنهايات المعقدة")
        
        # تحليل الأداء بالألوان
        white_games = [g for g in games if g['player_color'] == 'white']
        black_games = [g for g in games if g['player_color'] == 'black']
        
        white_win_rate = calculate_win_rate(white_games)
        black_win_rate = calculate_win_rate(black_games)
        
        if white_win_rate > 60:
            strengths.append("أداء ممتاز عند اللعب بالقطع البيضاء")
        elif white_win_rate < 45:
            weaknesses.append("يحتاج تحسين الافتتاحيات بالقطع البيضاء")
            recommendations.append("ادرس افتتاحيات e4 و d4 الأساسية")
        
        if black_win_rate > 50:  # للأسود معدل جيد
            strengths.append("دفاع قوي ومتين بالقطع السوداء")
        elif black_win_rate < 35:
            weaknesses.append("يحتاج تطوير مهارات الدفاع بالقطع السوداء")
            recommendations.append("تعلم دفاعات صلبة مثل الفرنسي وكارو-كان")
        
        # تحليل جودة المباريات
        avg_quality = sum(g.get('game_quality', 0) for g in games) / len(games)
        if avg_quality >= 7:
            strengths.append("جودة عالية في المباريات بشكل عام")
        elif avg_quality <= 4:
            weaknesses.append("يحتاج تحسين جودة القرارات في المباراة")
            recommendations.append("راجع مبارياتك وحلل الأخطاء")
        
        # إضافة نصائح عامة
        if not strengths:
            strengths.append("لاعب في مرحلة التطوير مع إمكانات جيدة")
        
        if not weaknesses:
            weaknesses.append("أداء متوازن نسبياً في معظم المجالات")
        
        if not recommendations:
            recommendations.append("استمر في اللعب والتدريب المنتظم")
        
        return {
            'strengths': strengths[:8],  # حد أقصى 8 نقاط قوة
            'weaknesses': weaknesses[:8],  # حد أقصى 8 نقاط ضعف
            'recommendations': recommendations[:10],  # حد أقصى 10 توصيات
            'game_length_analysis': {
                'short': {
                    'games': len(short_games), 
                    'wins': sum(1 for g in short_games if g['player_result'] == 'فوز'),
                    'win_rate': round(short_win_rate, 1)
                },
                'medium': {
                    'games': len(medium_games),
                    'wins': sum(1 for g in medium_games if g['player_result'] == 'فوز'),
                    'win_rate': round(medium_win_rate, 1)
                },
                'long': {
                    'games': len(long_games),
                    'wins': sum(1 for g in long_games if g['player_result'] == 'فوز'),
                    'win_rate': round(long_win_rate, 1)
                }
            },
            'detailed_analysis': {
                'avg_game_quality': round(avg_quality, 1),
                'white_performance': round(white_win_rate, 1),
                'black_performance': round(black_win_rate, 1),
                'opening_diversity': len(set(g.get('opening', '') for g in games)),
                'rated_games_ratio': len([g for g in games if g.get('rated', False)]) / len(games) * 100 if games else 0
            }
        }

    # باقي الدوال المساعدة
    def analyze_performance_by_color(self, games):
        """تحليل الأداء حسب لون القطع"""
        white_stats = {'games': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'total_moves': 0}
        black_stats = {'games': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'total_moves': 0}
        
        for game in games:
            target_stats = white_stats if game['player_color'] == 'white' else black_stats
            
            target_stats['games'] += 1
            target_stats['total_moves'] += game.get('total_moves', 0)
            
            if game['player_result'] == 'فوز':
                target_stats['wins'] += 1
            elif game['player_result'] == 'خسارة':
                target_stats['losses'] += 1
            else:
                target_stats['draws'] += 1
        
        # حساب المعدلات والمتوسطات
        for stats in [white_stats, black_stats]:
            if stats['games'] > 0:
                stats['win_rate'] = round((stats['wins'] / stats['games']) * 100, 1)
                stats['avg_moves'] = round(stats['total_moves'] / stats['games'], 1)
            else:
                stats['win_rate'] = 0
                stats['avg_moves'] = 0
        
        return {
            'white': white_stats,
            'black': black_stats,
            'preferred_color': 'white' if white_stats['win_rate'] > black_stats['win_rate'] else 'black',
            'color_balance': abs(white_stats['win_rate'] - black_stats['win_rate'])
        }

    def analyze_time_controls(self, games):
        """تحليل أنواع التحكم الزمني المحسن"""
        time_controls = defaultdict(lambda: {
            'games': 0, 'wins': 0, 'losses': 0, 'draws': 0,
            'avg_moves': 0, 'total_moves': 0
        })
        
        for game in games:
            tc = self.normalize_time_control(game.get('time_control', 'غير محدد'))
            time_controls[tc]['games'] += 1
            time_controls[tc]['total_moves'] += game.get('total_moves', 0)
            
            if game['player_result'] == 'فوز':
                time_controls[tc]['wins'] += 1
            elif game['player_result'] == 'خسارة':
                time_controls[tc]['losses'] += 1
            else:
                time_controls[tc]['draws'] += 1
        
        # حساب المعدلات
        for tc_data in time_controls.values():
            if tc_data['games'] > 0:
                tc_data['win_rate'] = round((tc_data['wins'] / tc_data['games']) * 100, 1)
                tc_data['avg_moves'] = round(tc_data['total_moves'] / tc_data['games'], 1)
            else:
                tc_data['win_rate'] = 0
                tc_data['avg_moves'] = 0
        
        return dict(time_controls)

    def normalize_time_control(self, time_control):
        """توحيد تسمية أنواع التحكم الزمني"""
        tc_lower = str(time_control).lower()
        
        if 'bullet' in tc_lower or '60' in tc_lower or '1+0' in tc_lower:
            return 'Bullet (1 دقيقة)'
        elif 'blitz' in tc_lower or ('180' in tc_lower or '3+0' in tc_lower or '5+0' in tc_lower):
            return 'Blitz (3-5 دقائق)'
        elif 'rapid' in tc_lower or ('600' in tc_lower or '10+0' in tc_lower or '15+' in tc_lower):
            return 'Rapid (10+ دقائق)'
        elif 'daily' in tc_lower or 'correspondence' in tc_lower:
            return 'مراسلة يومية'
        else:
            return time_control

    def analyze_performance_trends(self, games):
        """تحليل اتجاهات الأداء عبر الوقت"""
        if not games or len(games) < 5:
            return {
                'trend': 'غير كافي',
                'message': 'تحتاج لمزيد من المباريات (5 على الأقل) لتحليل الاتجاه'
            }
        
        # ترتيب المباريات حسب التاريخ
        try:
            sorted_games = sorted(games, key=lambda x: x.get('date', '1900.01.01'))
        except:
            return {'trend': 'خطأ في البيانات', 'message': 'تعذر ترتيب المباريات حسب التاريخ'}
        
        total_games = len(sorted_games)
        split_point = max(5, total_games // 2)
        
        recent_games = sorted_games[-split_point:]
        older_games = sorted_games[:-split_point]
        
        recent_wins = sum(1 for g in recent_games if g['player_result'] == 'فوز')
        older_wins = sum(1 for g in older_games if g['player_result'] == 'فوز') if older_games else 0
        
        recent_win_rate = (recent_wins / len(recent_games)) * 100 if recent_games else 0
        older_win_rate = (older_wins / len(older_games)) * 100 if older_games else 50
        
        improvement = recent_win_rate - older_win_rate
        
        # تحديد الاتجاه
        if improvement > 15:
            trend = "تحسن كبير جداً"
        elif improvement > 10:
            trend = "تحسن كبير"
        elif improvement > 5:
            trend = "تحسن ملحوظ"
        elif improvement > -5:
            trend = "مستقر"
        elif improvement > -10:
            trend = "تراجع طفيف"
        elif improvement > -15:
            trend = "تراجع ملحوظ"
        else:
            trend = "تراجع كبير"
        
        return {
            'trend': trend,
            'recent_win_rate': round(recent_win_rate, 1),
            'older_win_rate': round(older_win_rate, 1),
            'improvement': round(improvement, 1),
            'recent_games_count': len(recent_games),
            'older_games_count': len(older_games),
            'confidence': 'عالية' if total_games >= 20 else 'متوسطة' if total_games >= 10 else 'منخفضة'
        }

    def calculate_monthly_stats(self, games):
        """حساب الإحصائيات الشهرية المحسنة"""
        monthly_data = defaultdict(lambda: {
            'games': 0, 'wins': 0, 'losses': 0, 'draws': 0,
            'total_moves': 0, 'openings': defaultdict(int),
            'quality_sum': 0, 'rated_games': 0
        })
        
        for game in games:
            try:
                date_str = game.get('date', '')
                if date_str and '.' in date_str:
                    date_parts = date_str.split('.')
                    if len(date_parts) >= 2:
                        year = date_parts[0]
                        month = date_parts[1].zfill(2)
                        month_key = f"{year}-{month}"
                    else:
                        continue
                else:
                    continue
                
                stats = monthly_data[month_key]
                stats['games'] += 1
                stats['total_moves'] += game.get('total_moves', 0)
                stats['quality_sum'] += game.get('game_quality', 0)
                stats['openings'][game.get('opening', 'غير محدد')] += 1
                
                if game.get('rated', False):
                    stats['rated_games'] += 1
                
                if game['player_result'] == 'فوز':
                    stats['wins'] += 1
                elif game['player_result'] == 'خسارة':
                    stats['losses'] += 1
                else:
                    stats['draws'] += 1
                    
            except Exception as e:
                print(f"Error processing date for monthly stats: {e}")
                continue
        
        # تحويل وحساب المعدلات
        result = {}
        for month, stats in monthly_data.items():
            if stats['games'] > 0:
                result[month] = {
                    'games': stats['games'],
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'draws': stats['draws'],
                    'win_rate': round((stats['wins'] / stats['games']) * 100, 1),
                    'avg_moves': round(stats['total_moves'] / stats['games'], 1),
                    'avg_quality': round(stats['quality_sum'] / stats['games'], 1),
                    'rated_percentage': round((stats['rated_games'] / stats['games']) * 100, 1),
                    'top_opening': max(stats['openings'].items(), key=lambda x: x[1])[0] if stats['openings'] else 'غير محدد',
                    'opening_diversity': len(stats['openings'])
                }
        
        return result

    def identify_opening_detailed(self, moves):
        """تحديد الافتتاحية بدقة من النقلات"""
        if not moves or len(moves) < 2:
            return "غير محدد"
        
        # أول نقلتين
        first_move = moves[0]['move']
        second_move = moves[1]['move'] if len(moves) >= 2 else ''
        
        # البحث المباشر في قاعدة البيانات
        opening_key = f"{first_move} {second_move}".strip()
        if opening_key in self.opening_database:
            return opening_key
        
        # البحث بالنقلة الأولى فقط
        for key in self.opening_database.keys():
            if key.startswith(first_move):
                if len(moves) >= 2 and second_move in key:
                    return key
        
        # تصنيف بناءً على النقلة الأولى
        opening_classifications = {
            'e4': 'e4 e5',
            'd4': 'd4 d5',
            'Nf3': 'Nf3 d5',
            'c4': 'c4',
            'g3': 'g3',
            'f4': 'f4'
        }
        
        return opening_classifications.get(first_move, "افتتاحية أخرى")

    def get_player_result(self, result, player_color):
        """تحديد نتيجة اللاعب"""
        if result == '1/2-1/2':
            return 'تعادل'
        elif result == '1-0':
            return 'فوز' if player_color == 'white' else 'خسارة'
        elif result == '0-1':
            return 'فوز' if player_color == 'black' else 'خسارة'
        else:
            return 'غير مكتملة'

    def estimate_duration(self, moves):
        """تقدير مدة المباراة بالدقائق المحسن"""
        if not moves:
            return 0
        
        num_moves = len(moves)
        
        # تقدير أكثر دقة بناءً على عدد النقلات ونوع المباراة
        if num_moves < 20:  # مباراة سريعة جداً
            base_time = num_moves * 25  # 25 ثانية لكل نقلة
        elif num_moves < 40:  # مباراة متوسطة
            base_time = num_moves * 45  # 45 ثانية لكل نقلة
        elif num_moves < 60:  # مباراة طويلة
            base_time = num_moves * 60  # دقيقة لكل نقلة
        else:  # مباراة طويلة جداً
            base_time = num_moves * 75  # دقيقة وربع لكل نقلة
        
        # إضافة وقت التفكير
        thinking_time = min(600, num_moves * 10)  # حد أقصى 10 دقائق إضافية
        
        total_seconds = base_time + thinking_time
        return max(1, total_seconds // 60)

# إنشاء مثيل المحلل
analyzer = AdvancedChessAnalyzer()

# المسارات الأساسية
@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """التحليل الأساسي - الإصدار المحسن"""
    data = request.get_json()
    username = data.get('username', '').strip()
    max_games = int(data.get('max_games', 20))
    
    if not username:
        return jsonify({'error': 'يرجى إدخال اسم المستخدم'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل'}), 400
    
    try:
        print(f"🔍 Starting basic analysis for {username} ({max_games} games)...")
        
        # جلب معلومات اللاعب
        player_info = analyzer.fetch_player_info(username)
        if not player_info:
            return jsonify({'error': f'لم يتم العثور على اللاعب "{username}". تأكد من الاسم.'}), 404
        
        # جلب المباريات
        games = analyzer.fetch_all_player_games(username, max_games)
        if not games:
            return jsonify({'error': 'لم يتم العثور على مباريات للاعب'}), 404
        
        # إحصائيات بسيطة محسنة
        stats = {
            'total_games': len(games),
            'wins': len([g for g in games if g['player_result'] == 'فوز']),
            'losses': len([g for g in games if g['player_result'] == 'خسارة']),
            'draws': len([g for g in games if g['player_result'] == 'تعادل']),
            'avg_moves': round(sum([g['total_moves'] for g in games]) / len(games), 1) if games else 0,
            'total_time': round(sum([g.get('game_duration', 0) for g in games]) / 60, 1),  # بالساعات
            'avg_quality': round(sum([g.get('game_quality', 0) for g in games]) / len(games), 1) if games else 0
        }
        
        if stats['total_games'] > 0:
            stats['win_rate'] = round((stats['wins'] / stats['total_games']) * 100, 1)
        else:
            stats['win_rate'] = 0
        
        # تحليل إضافي بسيط
        white_games = [g for g in games if g['player_color'] == 'white']
        black_games = [g for g in games if g['player_color'] == 'black']
        
        stats['white_win_rate'] = round((len([g for g in white_games if g['player_result'] == 'فوز']) / len(white_games) * 100), 1) if white_games else 0
        stats['black_win_rate'] = round((len([g for g in black_games if g['player_result'] == 'فوز']) / len(black_games) * 100), 1) if black_games else 0
        
        # حفظ في الجلسة
        basic_analysis = {
            'username': username,
            'player_info': player_info,
            'games': games,
            'stats': stats,
            'analysis_type': 'basic',
            'timestamp': int(time.time())
        }
        
        session['basic_analysis'] = basic_analysis
        session.permanent = True
        
        print(f"✅ Basic analysis completed for {username}!")
        
        return jsonify({
            'success': True,
            'username': username,
            'player_info': player_info,
            'games': games,
            'stats': stats
        })
        
    except Exception as e:
        print(f"❌ Error in basic analysis: {e}")
        return jsonify({'error': 'حدث خطأ أثناء التحليل الأساسي'}), 500

@app.route('/analyze_advanced', methods=['POST'])
def analyze_advanced():
    """التحليل المتقدم - الحل النهائي لمشكلة الجلسة"""
    data = request.get_json()
    username = data.get('username', '').strip()
    max_games = int(data.get('max_games', 50))
    
    if not username:
        return jsonify({'error': 'يرجى إدخال اسم المستخدم'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل'}), 400
    
    try:
        print(f"🚀 Starting advanced analysis for {username} ({max_games} games)...")
        
        # التحليل المتقدم الكامل
        full_analysis = analyzer.analyze_all_games_advanced(username, max_games)
        
        if not full_analysis:
            return jsonify({'error': 'لم يتم العثور على مباريات للاعب أو حدث خطأ في التحليل'}), 404
        
        # حفظ البيانات الكاملة في ملف مؤقت
        analysis_id = session_manager.save_analysis(full_analysis)
        
        if not analysis_id:
            return jsonify({'error': 'فشل في حفظ بيانات التحليل'}), 500
        
        # حفظ فقط المعرف والبيانات الأساسية في الجلسة
        session_data = {
            'analysis_id': analysis_id,
            'username': username,
            'total_analyzed': full_analysis['total_analyzed'],
            'analysis_type': 'advanced',
            'created_at': int(time.time()),
            'expires_at': int(time.time()) + 14400  # 4 ساعات
        }
        
        session['analysis_ref'] = session_data
        session.permanent = True
        
        print(f"✅ Advanced analysis completed and saved for {username}!")
        print(f"💾 Analysis ID: {analysis_id}")
        print(f"📊 Session size: {len(str(session_data))} characters (reduced from full data)")
        
        # إرجاع ملخص للعرض
        summary = {
            'username': username,
            'total_analyzed': full_analysis['total_analyzed'],
            'analysis_id': analysis_id,
            'games': full_analysis['games'][:5],  # أول 5 مباريات للعرض
            'advanced_stats': {
                'openings_analysis': {
                    'total_openings_count': full_analysis['advanced_stats']['openings_analysis']['total_openings_count']
                },
                'strengths_and_weaknesses': {
                    'strengths': full_analysis['advanced_stats']['strengths_and_weaknesses']['strengths'][:3],
                    'weaknesses': full_analysis['advanced_stats']['strengths_and_weaknesses']['weaknesses'][:3]
                },
                'trend_analysis': full_analysis['advanced_stats']['trend_analysis']
            }
        }
        
        return jsonify({
            'success': True,
            'analysis': summary,
            'message': 'تم إكمال التحليل المتقدم بنجاح'
        })
        
    except Exception as e:
        print(f"❌ Error in advanced analysis: {e}")
        return jsonify({'error': f'حدث خطأ أثناء التحليل المتقدم: {str(e)}'}), 500

# تحديث مسارات الصفحات
@app.route('/deep_analysis')
def deep_analysis():
    """صفحة التحليل العميق - الحل المحدث"""
    analysis_ref = session.get('analysis_ref')
    
    if not analysis_ref or not analysis_ref.get('analysis_id'):
        print("⚠️ No analysis reference found in session")
        return redirect(url_for('index'))
    
    # التحقق من انتهاء الصلاحية
    if int(time.time()) > analysis_ref.get('expires_at', 0):
        print("⚠️ Analysis reference expired")
        session.pop('analysis_ref', None)
        return redirect(url_for('index'))
    
    # تحميل البيانات الكاملة من الملف
    analysis = session_manager.load_analysis(analysis_ref['analysis_id'])
    
    if not analysis:
        print("⚠️ Failed to load analysis data")
        session.pop('analysis_ref', None)
        return redirect(url_for('index'))
    
    print(f"✅ Loading deep analysis for {analysis.get('username', 'Unknown')}")
    return render_template('deep_analysis.html', analysis=analysis)

@app.route('/statistics')
def statistics():
    """صفحة الإحصائيات المتقدمة - محدثة"""
    analysis_ref = session.get('analysis_ref')
    
    if not analysis_ref or not analysis_ref.get('analysis_id'):
        print("⚠️ No analysis reference found")
        return redirect(url_for('index'))
    
    if int(time.time()) > analysis_ref.get('expires_at', 0):
        print("⚠️ Analysis expired")
        session.pop('analysis_ref', None)
        return redirect(url_for('index'))
    
    analysis = session_manager.load_analysis(analysis_ref['analysis_id'])
    
    if not analysis:
        print("⚠️ Failed to load analysis for statistics")
        return redirect(url_for('index'))
    
    return render_template('statistics.html', analysis=analysis)

@app.route('/filter_games')
def filter_games():
    """صفحة تصفية المباريات - محدثة"""
    analysis_ref = session.get('analysis_ref') or session.get('basic_analysis')
    
    if not analysis_ref:
        print("⚠️ No analysis found")
        return redirect(url_for('index'))
    
    # للتحليل المتقدم
    if analysis_ref.get('analysis_id'):
        if int(time.time()) > analysis_ref.get('expires_at', 0):
            session.pop('analysis_ref', None)
            return redirect(url_for('index'))
        
        analysis = session_manager.load_analysis(analysis_ref['analysis_id'])
        if not analysis:
            return redirect(url_for('index'))
    else:
        # للتحليل الأساسي
        analysis = analysis_ref
    
    return render_template('filter_games.html', analysis=analysis)

@app.route('/game_analysis/<int:game_id>')
def game_analysis(game_id):
    """صفحة تحليل مباراة محددة - محدثة"""
    analysis_ref = session.get('analysis_ref') or session.get('basic_analysis')
    
    if not analysis_ref:
        return redirect(url_for('index'))
    
    analysis = None
    
    # للتحليل المتقدم
    if analysis_ref.get('analysis_id'):
        if int(time.time()) > analysis_ref.get('expires_at', 0):
            session.pop('analysis_ref', None)
            return redirect(url_for('index'))
        
        analysis = session_manager.load_analysis(analysis_ref['analysis_id'])
    else:
        # للتحليل الأساسي
        analysis = analysis_ref
    
    if not analysis or game_id >= len(analysis.get('games', [])) or game_id < 0:
        return redirect(url_for('index'))
    
    game = analysis['games'][game_id]
    return render_template('game_analysis.html', game=game, game_id=game_id, analysis=analysis)

@app.route('/results')
def results():
    """صفحة النتائج الأساسية - محسنة"""
    analysis = session.get('analysis_ref') or session.get('basic_analysis')
    
    if not analysis:
        print("⚠️ No analysis found in session")
        return redirect(url_for('index'))
    
    # للتحليل المتقدم
    if analysis.get('analysis_id'):
        if int(time.time()) > analysis.get('expires_at', 0):
            session.pop('analysis_ref', None)
            return redirect(url_for('index'))
        
        full_analysis = session_manager.load_analysis(analysis['analysis_id'])
        if not full_analysis:
            return redirect(url_for('index'))
        analysis = full_analysis
    
    print(f"✅ Loading results for {analysis.get('username', 'Unknown')}")
    return render_template('results.html', analysis=analysis)

@app.route('/batch_analysis')
def batch_analysis():
    """صفحة التحليل المقارن"""
    return render_template('batch_analysis.html')

# APIs محسنة
@app.route('/api/player_search', methods=['GET'])
def player_search():
    """البحث عن لاعب - محسن"""
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'اسم المستخدم مطلوب'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'اسم المستخدم قصير جداً'}), 400
    
    try:
        player_info = analyzer.fetch_player_info(username)
        
        if player_info:
            return jsonify({
                'success': True,
                'player': {
                    'username': player_info.get('username', username),
                    'name': player_info.get('name', ''),
                    'title': player_info.get('title', ''),
                    'followers': player_info.get('followers', 0),
                    'country': player_info.get('country', ''),
                    'joined': player_info.get('joined', ''),
                    'avatar': player_info.get('avatar', ''),
                    'is_streamer': player_info.get('is_streamer', False),
                    'status': player_info.get('status', 'basic')
                }
            })
        else:
            return jsonify({'error': 'لم يتم العثور على اللاعب'}), 404
            
    except Exception as e:
        print(f"Error in player search: {e}")
        return jsonify({'error': 'خطأ في البحث عن اللاعب'}), 500

# تحديث API session_status
@app.route('/api/session_status')
def session_status():
    """فحص حالة الجلسة - محدث"""
    try:
        basic_analysis = session.get('basic_analysis')
        analysis_ref = session.get('analysis_ref')
        
        # التحقق من التحليل المتقدم
        has_advanced = False
        advanced_username = None
        advanced_games = 0
        
        if analysis_ref and analysis_ref.get('analysis_id'):
            # التحقق من انتهاء الصلاحية
            if int(time.time()) <= analysis_ref.get('expires_at', 0):
                # محاولة تحميل البيانات للتأكد
                analysis_data = session_manager.load_analysis(analysis_ref['analysis_id'])
                if analysis_data:
                    has_advanced = True
                    advanced_username = analysis_ref.get('username')
                    advanced_games = analysis_ref.get('total_analyzed', 0)
                else:
                    # حذف المرجع المنتهي الصلاحية
                    session.pop('analysis_ref', None)
            else:
                # حذف المرجع المنتهي الصلاحية
                session.pop('analysis_ref', None)
        
        # معلومات التخزين
        storage_info = session_manager.get_storage_info()
        
        return jsonify({
            'has_basic_analysis': basic_analysis is not None,
            'has_advanced_analysis': has_advanced,
            'session_keys': list(session.keys()),
            'basic_analysis_username': basic_analysis.get('username') if basic_analysis else None,
            'advanced_analysis_username': advanced_username,
            'basic_analysis_games': len(basic_analysis.get('games', [])) if basic_analysis else 0,
            'advanced_analysis_games': advanced_games,
            'session_size_kb': len(str(session)) / 1024,
            'timestamp': int(time.time()),
            'analysis_expires_at': analysis_ref.get('expires_at') if analysis_ref else None,
            'storage_files': storage_info['files'],
            'storage_size_mb': storage_info['size_mb']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export_analysis', methods=['POST'])
def export_analysis():
    """تصدير التحليل - محسن"""
    analysis_ref = session.get('analysis_ref') or session.get('basic_analysis')
    
    if not analysis_ref:
        return jsonify({'error': 'لا يوجد تحليل للتصدير'}), 400
    
    try:
        analysis = None
        
        # للتحليل المتقدم
        if analysis_ref.get('analysis_id'):
            analysis = session_manager.load_analysis(analysis_ref['analysis_id'])
        else:
            # للتحليل الأساسي
            analysis = analysis_ref
        
        if not analysis:
            return jsonify({'error': 'فشل في تحميل بيانات التحليل'}), 400
        
        # إعداد البيانات للتصدير
        export_data = {
            'player': analysis['username'],
            'analysis_date': datetime.now().isoformat(),
            'analysis_type': analysis.get('analysis_type', 'unknown'),
            'total_games': analysis.get('total_analyzed', len(analysis.get('games', []))),
            'export_version': '3.1'
        }
        
        # إضافة الإحصائيات الأساسية
        if 'stats' in analysis:
            export_data['summary'] = analysis['stats']
        elif 'games' in analysis:
            games = analysis['games']
            export_data['summary'] = {
                'win_rate': round((len([g for g in games if g['player_result'] == 'فوز']) / len(games)) * 100, 1),
                'total_wins': len([g for g in games if g['player_result'] == 'فوز']),
                'total_losses': len([g for g in games if g['player_result'] == 'خسارة']),
                'total_draws': len([g for g in games if g['player_result'] == 'تعادل'])
            }
        
        # إضافة التحليل المتقدم إذا وجد
        if 'advanced_stats' in analysis:
            advanced_stats = analysis['advanced_stats']
            export_data.update({
                'strengths': advanced_stats.get('strengths_and_weaknesses', {}).get('strengths', []),
                'weaknesses': advanced_stats.get('strengths_and_weaknesses', {}).get('weaknesses', []),
                'recommendations': advanced_stats.get('strengths_and_weaknesses', {}).get('recommendations', []),
                'performance_by_color': advanced_stats.get('performance_by_color', {}),
                'trends': advanced_stats.get('trend_analysis', {}),
                'openings_summary': {
                    'total_openings': advanced_stats.get('openings_analysis', {}).get('total_openings_count', 0),
                    'best_as_white': advanced_stats.get('openings_analysis', {}).get('best_as_white'),
                    'best_as_black': advanced_stats.get('openings_analysis', {}).get('best_as_black')
                }
            })
        
        return jsonify({
            'success': True,
            'data': export_data,
            'filename_suggestion': f"chess-analysis-{analysis['username']}-{datetime.now().strftime('%Y%m%d')}.json"
        })
        
    except Exception as e:
        print(f"Error in export: {e}")
        return jsonify({'error': 'فشل في تصدير البيانات'}), 500

# إعدادات التطبيق والأخطاء
@app.before_request
def before_request():
    """إعداد الطلبات"""
    if 'initialized' not in session:
        session['initialized'] = True
        session.permanent = True

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# إضافة تنظيف تلقائي للملفات
def cleanup_job():
    """مهمة تنظيف دورية"""
    session_manager.cleanup_old_files()

# جدولة تنظيف كل ساعة
schedule.every().hour.do(cleanup_job)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(300)  # فحص كل 5 دقائق

# بدء المجدول في thread منفصل
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

if __name__ == '__main__':
    print("🚀 Starting Chess Analyzer Algeria Advanced v3.1...")
    print("🌐 Server will be available at:")
    print("   - Local: http://127.0.0.1:5000")
    print("   - Network: http://192.168.x.x:5000")
    print("⚡ Debug mode: ON")
    print("🔒 Session lifetime: 4 hours")
    print("💾 File-based storage for large analysis data")
    
    # تنظيف الملفات القديمة عند البدء
    session_manager.cleanup_old_files()
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
