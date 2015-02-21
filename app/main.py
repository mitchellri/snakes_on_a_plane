import bottle
import json
import heapq
import random
import copy

################################################################################
# Constants                                                                    #
################################################################################
snakeName = 'snakes-on-a-plane'
directions = {
	(-1, 0): 'left',
	(1, 0): 'right',
	(0, -1): 'up',
	(0, 1): 'down'
}

trapSamples = 10
trapEscapePercentageNeeded = 0.5

################################################################################
# Classes                                                                      #
################################################################################

##
# Basic priority queue, minimum value at top
#
class PriorityQueue:
	def __init__(self):
		self.elements = []
	
	def empty(self):
		return len(self.elements) == 0
	
	def enqueue(self, element, priority):
		heapq.heappush(self.elements, (priority, element))
	
	def dequeue(self):
		return heapq.heappop(self.elements)[1]

##
# Used for converting backwards path returned by A* to forwards, also finding
# direction to move
#

def pathCameFrom(cameFrom, goal):
	goTo = { goal: None }
	start = goal
	while cameFrom[start]:
		goTo[cameFrom[start]] = start
		start = cameFrom[start]
	return Path(goTo, start)

class Path:
	def __init__(self, goTo, start):
		self.goTo = goTo
		self.start = start

	def direction(self):
		nxt = self.goTo[self.start]
		return (nxt[0] - self.start[0], nxt[1] - self.start[1])

##
# Grid to use for pathfinding, has obstructions to be navigated around
#
class Grid:
	def __init__(self, width, height):
		self.width = width
		self.height = height
		self.cells = [ [ 0 for y in range(height) ] for x in range(width) ]
	
	# Finds a random, unobstructed cell on the grid
	def random(self):
		cell = None
		while cell == None or self.obstructed(cell):
			x = random.randint(0, self.width - 1)
			y = random.randint(0, self.height - 1)
			cell = (x, y)
		return cell

	# Checks if the grid contains a cell
	def contains(self, cell):
		return (cell[0] >= 0
			and cell[1] >= 0
			and cell[0] < self.width
			and cell[1] < self.height)

	# Obstructs a cell on the grid
	def obstruct(self, cell):
		self.cells[cell[0]][cell[1]] = 1
	
	# Checks if a cell on the grid is obstructed
	def obstructed(self, cell):
		return self.cells[cell[0]][cell[1]] == 1

	# Heuristic for pathfinding, not currently used for anything
	# most likely use it to represent risk
	def heuristic(self, cell):
		return self.cells[cell[0]][cell[1]]

	# Finds neighbours to a cell on the grid
	def neighbours(self, cell):
		neighbours = []
		for direction in directions:
			neighbour = (cell[0] + direction[0], cell[1] + direction[1])
			
			# Check if on grid, and not obstructed
			if self.contains(neighbour) and not self.obstructed(neighbour):
				neighbours.append(neighbour)
		
		return neighbours

################################################################################
# Functions                                                                    #
################################################################################

# xDist + yDist
def manDist(a, b):
	return abs(a[0] - b[0]) + abs(a[1] - b[1])

# A* search, uses grid's heuristic
def aStar(grid, start, goal):
	frontier = PriorityQueue()
	frontier.enqueue(start, 0)
	cameFrom = { start: None }
	costSoFar = { start: 0 }

	while not frontier.empty():
		current = frontier.dequeue()
		if current == goal:
			return pathCameFrom(cameFrom, goal)

		for neighbour in grid.neighbours(current):
			cost = costSoFar[current] + grid.heuristic(neighbour)

			if neighbour not in costSoFar or cost < costSoFar[neighbour]:
				costSoFar[neighbour] = cost
				priority = cost + manDist(neighbour, goal)
				frontier.enqueue(neighbour, priority)
				cameFrom[neighbour] = current
	return False

def ratePosition(grid, start, samples):
		passes = 0
		for i in range(samples):
			goal = grid.random()
			if aStar(grid, start, goal):
				passes += 1
		return float(passes) / samples

def isTrap(grid, start):
	score = ratePosition(grid, start, trapSamples)
	return score < trapEscapePercentageNeeded

def isPathTrap(grid, path):		#determine if we take a path or not
	grid = copy.deepcopy(grid)	#makes grid copy
	curr = path.start			#create iterator
	grid.obstruct(curr)			#go through grid and obstruct it
	while path.goTo[curr]:		#
		grid.obstruct(curr)
		curr = path.goTo[curr]
	return isTrap(grid, curr)
	

################################################################################
# Server                                                                       #
################################################################################

@bottle.get('/')
def index():
	return """<a href="https://github.com/sendwithus/battlesnake-python">battlesnake-python</a>"""
#-------------------------------------------------------------------------------
@bottle.post('/start')
def start():
	data = bottle.request.json
	# Request:
	#	game_id, width, height
	
	return json.dumps({
		'name': snakeName,
		'color': '#8B3626',
		'head_url': 'http://i.imgur.com/7hhZkaN.gif',
		'taunt': 'GRAWWRRGGGGGGGGGG!'
	})
#-------------------------------------------------------------------------------
@bottle.post('/move')
def move():
	data = bottle.request.json
	# Request:
	#	game_id, turn, board, snakes, food
	
	ourSnake = None
 	
	grid = Grid(len(data['board'][0]), len(data['board']))				#makes base grid
	for snake in data['snakes']:										#sorts through snakes
		for coord in snake['coords']:									#get all snake coords
			grid.obstruct(tuple(coord))									#make obstructions
		if snake['name'] != snakeName:									#if snake is not our snake
			for direction in directions:								#make all snake heads a obstruction
				if len(snake['coords']) >= len(ourSnake['coords']): 	# if other snake larger, then obstruct where it can move to
					head = snake['coords'][0]							#
					movement = (head[0] + direction[0], head[1] + direction[1])	#
					grid.obstruct(movement)								#
		else:
			ourSnake = snake
	
	#-------GET FOODS
	possibleFoods = []
	for food in data['food']:
		dist = manDist(tuple(ourSnake['coords'][0]), tuple(food))
		skip = False
		for snake in data['snakes']:
			if snake['name'] != snakeName and manDist(tuple(snake['coords'][0]), tuple(food)) <= dist:
				skip = True
				break
		if not skip:
			possibleFoods.append(tuple(food))
			
	#-------GET CLOSEST FOOD
	closestFoodDist = 0
	closestFood = None
	for food in possibleFoods:
		d = manDist(tuple(ourSnake['coords'][0]), food)
		if d < closestFoodDist or closestFood == None:
			closestFood = food
			closestFoodDist = d
	idle = False
	
	if closestFood != None:
		path = aStar(grid, tuple(ourSnake['coords'][0]), closestFood)
		if path != False and not isPathTrap(grid, path):
			move = directions[path.direction()]
		else:
			idle = True
	else:
		idle = True
	
	
	#------IDLE MOVEMENTS
	if idle:
		move = 'left'
	
	#------DIRECTION CHECK
	
	
	#------------------RETURN TO SERVER-----------
	return json.dumps({
		'move': move,
		'taunt': 'Feel the power of the mongoose!'
	})
	#---------------------------------------------
	
	
#-------------------------------------------------------------------------------
@bottle.post('/end')
def end():
	data = bottle.request.json
	# Request:
	#	game_id

	return json.dumps({})
#-------------------------------------------------------------------------------
# Expose WSGI app
application = bottle.default_app()