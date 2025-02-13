from direct.showbase.ShowBase import ShowBase
import random
from panda3d.core import Vec3, DirectionalLight, Vec4, CollisionNode, CollisionHandlerQueue, CollisionSphere, CollisionTraverser, BitMask32, CollisionBox
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel
from direct.task import Task
import sys
import math
import json
import os
class Player:
    #Spelaren med pengar och inventarie
    def __init__(self):
        self.money = 1000  # Startkapital
        self.inventory = {"Wood": 0, "Stone": 0, "Rum": 0, "Sugar": 0}  # Handelsvaror
        self.player_health = 100  # Spelarens hälsa
        
    # Spara spelarens data till en JSON-fil

    def save_game(self, file_name="player_save.json"):
        save_data = {
            "money": self.money,
            "inventory": self.inventory,
            "player_health": self.player_health,}

        # Absolut eller relativ väg
        file_path = os.path.join(os.getcwd(), file_name)  # Använder arbetskatalogen för att spara filen
        with open(file_path, "w") as file:
            json.dump(save_data, file)
        
        print(f"Spelet sparat på {file_path}!")  # Skriver ut var filen sparas

    def load_game(self, file_name="player_save.json"):
        try:
            # Absolut eller relativ väg
            file_path = os.path.join(os.getcwd(), file_name)  # Använder arbetskatalogen för att läsa filen
            if not os.path.exists(file_path):  # Kontrollera om filen finns
                print(f"Filen finns inte på {file_path}.")
                return

            with open(file_path, "r") as file:
                save_data = json.load(file)
                self.money = save_data["money"]
                self.inventory = save_data["inventory"]
                self.player_health = save_data["player_health"]
                
            print(f"Spelet laddat från {file_path}!")
        except FileNotFoundError:
            print(f"Ingen sparfil hittades på {file_path}.")
        except json.JSONDecodeError:
            print(f"Fel vid läsning av sparfilen på {file_path}. Kan vara korrupt.")
        
class Enemy:
    def __init__(self, model_path, pos, scale, health, render):
        self.model = loader.loadModel(model_path) # type: ignore
        self.model.reparentTo(render)
        self.model.setPos(pos)
        self.model.setScale(scale)
        self.health = health
        self.speed = 5
        
    def set_speed(self, speed):
        self.speed = speed  # Metod för att sätta hastigheten

    def get_speed(self):
        return self.speed  # Metod för att hämta hastigheten
    

    

class Projectile:
    def __init__(self, model_path, pos, speed, damage, render):
        self.model = loader.loadModel(model_path) # type: ignore
        self.model.reparentTo(render)
        self.model.setPos(pos)
        self.model.setScale(0.1)
        self.speed = speed
        self.damage = damage
        self.active = True  # För att kontrollera om projektilen är aktiv

    def move(self, dt):
        # Flytta projektilen framåt
        if self.active:
            self.model.setY(self.model, self.speed * dt)

    def destroy(self):
        # Ta bort projektilen
        if self.active:
            self.model.removeNode()
            self.active = False

class MyGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.cTrav = CollisionTraverser()
        self.notifier = CollisionHandlerQueue()
        self.player = Player()  # type: ignore # Skapa spelaren
        
        # Skapa en tangentbordsbindning för att spara spelet
        self.accept("s", self.save_game)
        self.accept("l", self.load_game)
        
        self.projectiles = []  # Lista för spelarens projektiler
        self.projectile_speed = 300  # Hastighet för projektiler
        self.projectile_damage = 20  # Skada som projektilen orsakar
        self.projectile_model = "models/kanonkula.glb"  # Modell för projektilen
        self.last_shot_time = 0  # Tidpunkt för senaste skottet
        self.shoot_delay = 0.5  # Fördröjning mellan skott i sekunder
        
        self.music = loader.loadSfx("sounds/PirateSong1.mp3")  # type: ignore # Ange rätt sökväg
        self.music.setLoop(True)  # Sätt musiken att loopa
        self.music.setVolume(0.1)  # Justera volymen (0.0 till 1.0)
        self.music.play()  # Spela musiken
        
        self.wave_sound = loader.loadSfx("sounds/SeaWavesSoundEffect.mp3")  # type: ignore # Ljud för vågor
        self.wave_sound.setLoop(True)  # Loop för konstant vågljud
        self.wave_sound.setVolume(0.5) # ange volym från 0.0 till 1.0
        self.wave_sound.play() # spelar ljudet

        self.bird_sound = loader.loadSfx("sounds/SeagullSoundEffect.mp3")  # type: ignore # Ljud för fåglar
        self.bird_sound.setLoop(True)
        self.bird_sound.setVolume(0.1)
        self.bird_sound.play() 

        self.cannon_sound = loader.loadSfx("sounds/CannonSoundEffect.mp3") # type: ignore
        self.cannon_sound.setVolume(0.1)
        
        # Bind skjutknapp
        self.accept("space", self.shoot)
        
        self.enemies = []
        self.add_enemy("models/skepp2.glb", Vec3(50, 50, 5), 0.3, 100)
        self.add_enemy("models/skepp2.glb", Vec3(-50, 50, 5), 0.3, 100)
        self.taskMgr.add(self.update_enemies, "updateEnemies")
        
        # Laddar spelar skeppet
        self.model = self.loader.loadModel("models/piratskepp6.glb")
        self.model.reparentTo(self.render)
        self.model.setScale(0.5, 0.5, 0.5)  # Skala skeppet
        self.model.setPos(0, 10, 5)  # Startposition


        # Skapar kollisionsnod för skeppet
        col = self.model.attachNewNode(CollisionNode("ship"))
        col.node().addSolid(CollisionBox(Vec3(0, 0, 0), 3, 10, 5))  # Kollisionsbox
        col.node().setFromCollideMask(BitMask32.bit(1))  # Skeppets kollisionsmask
        col.node().setIntoCollideMask(BitMask32.allOff())
        
        # Laddar en ö
        self.island = self.loader.loadModel("models/island3.glb")
        self.island.reparentTo(self.render)
        self.island.setScale(1, 1, 1)  # Skala ön
        self.island.setPos(30, 30, 8)  # Placera ön

        # Skapar kollisionsnod för ön
        col = self.island.attachNewNode(CollisionNode("Island"))
        col.node().addSolid(CollisionSphere(Vec3(0, 5, 0), 12))  # Kollisionssfär
        col.node().setFromCollideMask(BitMask32.allOff())
        col.node().setIntoCollideMask(BitMask32.bit(1))  # Matcha skeppets fromCollideMask #col.show() om man vill se hitbox
        
        
        # laddar in en annan ö
        self.island2 = self.loader.loadModel("models/island6.glb")
        self.island2.reparentTo(self.render)
        self.island2.setScale(2, 2, 2)  # Skala ön
        self.island2.setPos(80, 80, 6)  # Placera ön
        
        col = self.island2.attachNewNode(CollisionNode("Island"))
        col.node().addSolid(CollisionSphere(Vec3(-1, 5, 0), 5))  # Kollisionssfär
        col.node().setFromCollideMask(BitMask32.allOff())
        col.node().setIntoCollideMask(BitMask32.bit(1))  # Matcha skeppets fromCollideMask #col.show() om man vill se hitbox
        
        
        self.island3 = self.loader.loadModel("models/island8.glb")
        self.island3.reparentTo(self.render)
        self.island3.setScale(3, 3, 3)  # Skala ön
        self.island3.setPos(-100, -100, 8)  # Placera ön
        
        col = self.island3.attachNewNode(CollisionNode("Island"))
        col.node().addSolid(CollisionSphere(Vec3(0, 1, 0), 7))  # Kollisionssfär
        col.node().setFromCollideMask(BitMask32.allOff())
        col.node().setIntoCollideMask(BitMask32.bit(1))  # Matcha skeppets fromCollideMask #col.show() om man vill se hitbox
        
        
        self.setupCollisionDetection()
        self.taskMgr.add(self.update_projectiles, "UpdateProjectilesTask")
        
        self.inventory_label = DirectLabel(text=f"Money: {self.player.money}\nWood: {self.player.inventory['Wood']}\nStone: {self.player.inventory['Stone']}\nRum: {self.player.inventory['Rum']}\nSugar: {self.player.inventory['Sugar']}", 
        scale=0.05, pos=(-1.7, 0, 0.9),
        frameColor=(0.96, 0.91, 0.76, 1),
        )
        # type: ignore #inventory GUI
        
        self.trade_frame = None #Handelsmenyn
        

        # Ladda golvet (miljömodell)
        self.floor = self.loader.loadModel("models/environment")
        self.floor.reparentTo(self.render)
        self.floor.setScale(400, 400, 1)
        self.floor.setPos(0, 0, 0)
        water_texture = self.loader.loadTexture("textures/water.png")
        self.floor.setTexture(water_texture, 1)



        # Lägg till en ljuskälla
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(1, 1, 1, 1))  # Vitt ljus
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(-30, -60, 0)  # Ljusriktning
        self.render.setLight(dlnp)

        # Rörelse- och rotationshastighet
        self.speed = 100  # Hur snabbt spelarskeppet rör sig
        self.rotation_speed = 100  # Hur snabbt skeppet roterar
        

        # Tangentkontroll
        self.keys = {"forward": False, "backward": False, "left": False, "right": False}

        # Binda tangenttryckningar
        self.accept("escape", sys.exit)
        self.accept("arrow_up", self.set_key, ["forward", True])
        self.accept("arrow_up-up", self.set_key, ["forward", False])
        self.accept("arrow_down", self.set_key, ["backward", True])
        self.accept("arrow_down-up", self.set_key, ["backward", False])
        self.accept("arrow_left", self.set_key, ["left", True])
        self.accept("arrow_left-up", self.set_key, ["left", False])
        self.accept("arrow_right", self.set_key, ["right", True])
        self.accept("arrow_right-up", self.set_key, ["right", False])

        # Lägg till uppdateringsuppgifter
        self.taskMgr.add(self.update_player, "UpdatePandaTask")
        self.taskMgr.add(self.update_camera, "UpdateCameraTask")  # Ny uppgift för att uppdatera kameran
        self.taskMgr.add(self.update_game, "UpdateGameTask")
        
    def save_game(self):
        self.player.save_game() 
        self.update_inventory_label()  # Uppdatera UI efter sparning 
        
    def load_game(self):
        self.player.load_game()
        self.update_inventory_label()  # Uppdatera UI efter inläsning

        
    def set_key(self, key, value):
        #Uppdatera vilken tangent som är nedtryckt
        self.keys[key] = value

    def update_player(self, task):
        #Uppdatera spelarskeppet varje frame baserat på tangenttryckningar
        dt = globalClock.getDt()  # type: ignore # Tid sedan förra uppdateringen
        previous_pos = self.model.getPos()  # Spara skeppets nuvarande position

        # Rörelse framåt och bakåt
        if self.keys["forward"]:
            self.model.setPos(self.model, Vec3(0, self.speed * dt, 0))
        if self.keys["backward"]:
            self.model.setPos(self.model, Vec3(0, -self.speed * dt, 0))

        # Rotation vänster och höger
        if self.keys["left"]:
            self.model.setH(self.model.getH() + self.rotation_speed * dt)
        if self.keys["right"]:
            self.model.setH(self.model.getH() - self.rotation_speed * dt)

        # Kolla kollisioner
        self.cTrav.traverse(self.render)
        if self.check_player_collision():
            self.model.setPos(previous_pos)  # Återställ om det finns kollision

        return Task.cont  # Fortsätt köra denna uppgift varje frame

    def setupCollisionDetection(self):
        #Ställ in kollisionstraversering och notifiering
        self.notifier = CollisionHandlerQueue()  # Notifieringskö för kollisioner
        self.cTrav = CollisionTraverser()  # Kollisionstraverser

        # Lägg till kollisionsnoder i traversern
        ship_col_node = self.model.find("**/ship")
        self.cTrav.addCollider(ship_col_node, self.notifier)
        
        
    def add_enemy(self, model_path, pos, scale, health):
            enemy = Enemy(model_path, pos, scale, health, self.render)
            self.enemies.append(enemy)
            self.add_enemy_collision(enemy)

    def add_enemy_collision(self, enemy):
        print(f"Adding collision for enemy: {enemy.model.getName()}")
        # fäster kollisionsnoder till fienden
        enemy_col = enemy.model.attachNewNode(CollisionNode("enemy"))
        enemy_col.node().addSolid(CollisionBox(0, 5, 12, 5))  # kollisionszon för fiendeskepp
        enemy_col.node().setFromCollideMask(BitMask32.bit(2))  
        enemy_col.node().setIntoCollideMask(BitMask32.allOff())
        self.cTrav.addCollider(enemy_col, self.notifier) 
    
    
    def check_player_collision(self):
        #Kontrollera om spelarskeppet kolliderar med ön
        self.notifier.sortEntries()  # Sortera notifieringar
        for entry in self.notifier.entries:
            if entry.getFromNodePath().getParent() == self.model and entry.getIntoNode().getName() == "Island":
                print("Spelarskepp kolliderar med en ö!")
            return True
        return False
    
    def check_enemy_collision(self, enemy):
        # Kontrollera om fiendeskeppet kolliderar med ön
        self.notifier.sortEntries()  # Sortera notifieringar
        for entry in self.notifier.entries:
            from_node = entry.getFromNodePath().getParent()
            into_node = entry.getIntoNodePath().getParent()
            
            # Debugutskrift
            print(f"Checking collision: from {from_node.getName()} to {into_node.getName()}")

            # Kontrollera om kollision är mellan fiendeskepp och ö
            if from_node == enemy.model and "Island" in into_node.getName():
                print(f"From Node: {from_node.getName()}, Into Node: {into_node.getName()}")
                print(f"{enemy.model.getName()} kolliderar med en ö!")
                # Flytta fiendeskeppet bort från ön
                direction = enemy.model.getPos() - into_node.getPos()
                direction.normalize()
                enemy.model.setPos(enemy.model.getPos() + direction * enemy.get_speed() * globalClock.getDt()) # type: ignore
                return True
        return False
    
    def update_enemies(self, task):
        self.cTrav.traverse(self.render)  # kör traversern först

        for enemy in self.enemies:
            # räknar avstånd till spelaren
            direction = self.model.getPos() - enemy.model.getPos()

            # kollar kollison innan den kör
            if not self.check_enemy_collision(enemy):
                # rör fienden mot spelaren om ingen kollision upptäcks
                if direction.length() > 1.0:  # Optional: rör sig bara om fienden är tillräckligt långt borta
                    direction.normalize()
                    enemy.model.lookAt(self.model)  # gör så fiender är vända mot spelaren
                    speed = enemy.get_speed()  # får hastigheten för fiender
                    enemy.model.setPos(enemy.model.getPos() + direction * speed * globalClock.getDt())  # type: ignore # gör så fienden rör sig

        return Task.cont
    
    def shoot(self):
        # Kolla om fördröjningen är slut
        current_time = globalClock.getRealTime()  # type: ignore
        if current_time - self.last_shot_time < self.shoot_delay:
            print("tagga ner det är inget maskingevör!")
            return
        # Spela kanonljud vid skott
        self.cannon_sound.play()

        # Bestäm startposition och riktning för projektilen
        ship_pos = self.model.getPos()  # Skeppets globala position
        ship_heading = self.model.getH()  # Skeppets globala rotation (heading)

        # Skjut från vänster eller höger sida av skeppet
        side_offset = 2  # Avstånd från skeppets centrum till höger
        if hasattr(self, 'last_shot_side') and self.last_shot_side == "left":
            side_offset = -2  # Justering för vänster sida
            self.last_shot_side = "right"
        else:
            self.last_shot_side = "left"

        # Beräkna den globala skjutpositionen
        offset_direction = Vec3(side_offset, 0, 0)  # Förskjutning åt sidan i lokala koordinater
        shoot_position = self.model.getRelativePoint(self.model, offset_direction)

        # Justera för skeppets rotation
        heading_radians = math.radians(ship_heading)
        global_shoot_position = Vec3(
            ship_pos.getX() + side_offset * math.cos(heading_radians),
            ship_pos.getY() + side_offset * math.sin(heading_radians),
            ship_pos.getZ()
        )

        # Skapa en ny projektil vid den beräknade positionen
        projectile = Projectile(self.projectile_model, global_shoot_position, self.projectile_speed, self.projectile_damage, self.render)

        # Ställ in projektilens heading för att skjuta i rätt riktning (framåt i förhållande till skeppet)
        projectile.model.setH(ship_heading)
    
        # Lägg till projektilen i listan
        self.projectiles.append(projectile)

        self.last_shot_time = current_time
        print(f"Kula avfyrad från sidan: {global_shoot_position}, riktning: {ship_heading}")
        
    def update_projectiles(self, task):
        dt = globalClock.getDt() # type: ignore
        for projectile in self.projectiles:
            if projectile.active:
                projectile.move(dt)
                if self.check_projectile_collision(projectile):
                    projectile.destroy()
        return Task.cont
        
    def check_projectile_collision(self, projectile):
        # Kontrollera om projektilen träffar ett fiendeskepp
        for enemy in self.enemies:
            if projectile.model.getDistance(enemy.model) < 5:  # Justera avstånd för kollision
                enemy.health -= projectile.damage
                print(f"Hit enemy! Remaining health: {enemy.health}")
                if enemy.health <= 0:
                    self.destroy_enemy(enemy)
                return True
        return False

    def destroy_enemy(self, enemy):
        # Förstör ett fiendeskepp och belöna spelaren
        self.enemies.remove(enemy)
        enemy.model.removeNode()
        loot = random.choice(["Wood", "Stone", "Rum", "Sugar"])
        quantity = random.randint(2, 3)
        self.player.inventory[loot] += quantity
        print(f"Destroyed enemy! Loot: {quantity} {loot}")
        self.update_inventory_label()
        self.spawn_new_enemy()

    def spawn_new_enemy(self):
        # Spawn ett nytt fiendeskepp på en slumpmässig position
        x, y = random.randint(-100, 100), random.randint(-100, 100)
        self.add_enemy("models/skepp2.glb", Vec3(x, y, 5), 0.3, 100)
    

    def update_game(self, Task):
        #Uppdatera spelets logik varje frame
        self.cTrav.traverse(self.render)
        if self.check_player_collision():
            print("Spelare nära ön handel pågår")  # Felsökningsutskrift
            self.show_trade_menu()
        return Task.cont

    def show_trade_menu(self):
        #Visar handelsmenyn
        if self.trade_frame:
            print("Handelsmenyn är öppen")
            return  # Handelsmenyn är redan synlig

        #skapar ram för menyn
        print("skapar handelsmeny")
        self.trade_frame = DirectFrame(
            frameColor=(0.96, 0.91, 0.76, 0.8),
            frameSize=(-0.5, 0.5, -0.5, 0.5),
            pos=(0, 0, 0),
        )                                 

        DirectLabel(parent=self.trade_frame, text="Trade Menu", scale=0.1, pos=(0, 0, 0.4))

        # Köp knapp
        DirectButton(
            parent=self.trade_frame, text="Buy Wood (10 coins)", scale=0.04, pos=(-0.2, 0, 0.2),
            command=self.buy_item, extraArgs=["Wood", 10]
        )

        # Sälj knapp
        DirectButton(
            parent=self.trade_frame, text="Sell Wood (10 coins)", scale=0.04, pos=(0.2, 0, 0.2),
            command=self.sell_item, extraArgs=["Wood", 10]
        )

        # Stäng meny
        DirectButton(
            parent=self.trade_frame, text="Close", scale=0.08, pos=(0, 0, -0.4),
            command=self.hide_trade_menu
        )

        # köp knapp
        DirectButton(
            parent=self.trade_frame, text="Buy Stone (20 coins)", scale=0.04, pos=(-0.2, 0, 0.1),
            command=self.buy_item, extraArgs=["Stone", 20]
        )
        
        # Sälj knapp
        DirectButton(
            parent=self.trade_frame, text="Sell Stone (20 coins)", scale=0.04, pos=(0.2, 0, 0.1),
            command=self.sell_item, extraArgs=["Stone", 20]
        )


        # köp knapp
        DirectButton(
            parent=self.trade_frame, text="Buy Rum (50 coins)", scale=0.04, pos=(-0.2, 0, 0),
            command=self.buy_item, extraArgs=["Rum", 50]
        )

        # Sälj knapp
        DirectButton(
            parent=self.trade_frame, text="Sell Rum (50 coins)", scale=0.04, pos=(0.2, 0, 0),
            command=self.sell_item, extraArgs=["Rum", 50]
        )

        # köp knapp
        DirectButton(
            parent=self.trade_frame, text="Buy Sugar (40 coins)", scale=0.04, pos=(-0.2, 0, -0.1),
            command=self.buy_item, extraArgs=["Sugar", 40]
        )

        # Sälj knapp
        DirectButton(
            parent=self.trade_frame, text="Sell Sugar (40 coins)", scale=0.04, pos=(0.2, 0, -0.1),
            command=self.sell_item, extraArgs=["Sugar", 40]
        )

    def hide_trade_menu(self):
        #Döljer handelsmenyn
        if self.trade_frame:
            self.trade_frame.destroy()
            self.trade_frame = None

    def buy_item(self, item, cost):
        #Köper en vara om spelaren har tillräckligt med pengar
        if self.player.money >= cost:
            self.player.money -= cost
            self.player.inventory[item] += 1
            print(f"Bought 1 {item}. Remaining money: {self.player.money}")
            self.update_inventory_label()
        else:
            print("Not enough money!")

    def sell_item(self, item, price):
        #Säljer en vara om spelaren har varan i sin inventarie
        if self.player.inventory[item] > 0:
            self.player.inventory[item] -= 1
            self.player.money += price
            print(f"Sold 1 {item}. Total money: {self.player.money}")
            self.update_inventory_label()
        else:
            print(f"No {item} to sell!")

    def update_inventory_label(self):
        #Uppdaterar GUI för inventarie och pengar
        self.inventory_label["text"] = f"Money: {self.player.money}\nWood: {self.player.inventory['Wood']}\nStone: {self.player.inventory['Stone']}\nRum: {self.player.inventory['Rum']}\nSugar: {self.player.inventory['Sugar']}"

    def update_camera(self, task):
        #Uppdatera kamerans position för att följa spelar skeppet i tredjepersonsvy
        panda_pos = self.model.getPos()
        camera_x = panda_pos.getX() - 10  # Bakom spelar skeppet
        camera_y = panda_pos.getY() + 20  # Framför spelar skeppet
        camera_z = panda_pos.getZ() + 100  # Placera kameran högre
        self.camera.setPos(camera_x, camera_y, camera_z)
        self.camera.lookAt(self.model)
        return Task.cont  # Fortsätt köra denna uppgift varje frame
game = MyGame()
game.run()