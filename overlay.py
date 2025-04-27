import pygame
from settings import *
from player import *
from support import resource_path

class Overlay:
	#change
	def __init__(self, player):
		self.display_surface = pygame.display.get_surface()
		self.player = player
		self.font = pygame.font.Font(resource_path('font/PixeloidSans.ttf'), 20)
		self.items = ['hoe', 'axe', 'water', 'corn', 'tomato'] 
		self.items = player.inventory

		# 统一加载 5 个图标
		overlay_path = resource_path('images/overlay/')
		self.item_surf = {
			item: pygame.image.load((f'{overlay_path}{item}.png')).convert_alpha()
			for item in player.inventory
		}

		# 假设所有图标都是正方形且尺寸相同
		self.slot_size = next(iter(self.item_surf.values())).get_rect().width

		# 配色
		self.bg_color = (210, 180, 140)  # 浅棕
		self.border_color = (139, 69, 19)  # 棕
		self.selected_color = (0, 0, 255)  # 蓝

	#change
	def display(self):

		# # tool
		# tool_surf = self.tools_surf[self.player.selected_tool]
		# tool_rect = tool_surf.get_rect(midbottom = OVERLAY_POSITIONS['tool'])
		# self.display_surface.blit(tool_surf,tool_rect)
		#
		# # seeds
		# seed_surf = self.seeds_surf[self.player.selected_seed]
		# seed_rect = seed_surf.get_rect(midbottom = OVERLAY_POSITIONS['seed'])
		# self.display_surface.blit(seed_surf,seed_rect)

		n = len(self.items)  # 应该是 5
		total_w = self.slot_size * n
		start_x = (SCREEN_WIDTH - total_w) // 2
		y = SCREEN_HEIGHT - self.slot_size

		for idx, item in enumerate(self.items):
			x = start_x + idx * self.slot_size
			slot_rect = pygame.Rect(x, y, self.slot_size, self.slot_size)

			# 背景和边框
			pygame.draw.rect(self.display_surface, self.bg_color, slot_rect, 0)
			pygame.draw.rect(self.display_surface, self.border_color, slot_rect, 2)

			# 图标居中
			icon = self.item_surf[item]
			icon_rect = icon.get_rect(center=slot_rect.center)
			self.display_surface.blit(icon, icon_rect)

			if item in self.player.seed_inventory:  # 如果是种子
				count = self.player.seed_inventory[item]
			elif item in self.player.item_inventory:  # 如果是工具或其他物品
				count = self.player.item_inventory[item]
			else:
				count = 1  # 默认值
				
			# 渲染文本（白色字体，右下角偏移 5 像素）
			text_surf = self.font.render(str(count), True, 'white')
			text_rect = text_surf.get_rect(
				bottomright=slot_rect.move(-5, -5).bottomright
			)
			self.display_surface.blit(text_surf, text_rect)
        
			# 选中高亮
			if idx == self.player.selected_index:
				pygame.draw.rect(self.display_surface, self.selected_color,
								 slot_rect.inflate(-4, -4), 3)