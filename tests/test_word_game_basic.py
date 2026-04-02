import sys
import os

# 把项目根目录加入 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def test_word_game_module_import():
    import word_game
    assert word_game is not None