import random
import math
import matplotlib

from panda3d.core import AmbientLight,LVector4
from panda3d.core import Light, Spotlight
from direct.showbase.ShowBase import ShowBase
from direct.showbase.MessengerGlobal import messenger
from direct.gui.DirectLabel import DirectLabel
from direct.showbase import DirectObject

from panda3d.core import DepthOffsetAttrib, CullFaceAttrib
from panda3d.core import WindowProperties
# self written but public
from panda_object_create import panda_object_create_load
from panda_collisions import panda_collisions#CollisionWrapper
from panda_interface_glue import panda_interface_glue as pig
from panda3d.core import Point3
from vector import vector

from gamedevstuff import house

from my_save import sxml_main

class WorldObject:
    def __init__(self,myid):
        self.id = myid
        self.verts = []
        self.faces = [[0,1,2,3]] # this has to be a list of lists, with
        # one entry. best don't change this if you don't want to 
        # dig into how object creation works.

def get_position_elevation(point,cell):
    # or something.
    # I do have an average value for the center
    # or I have a center a specific elevation and then the corner
    # points are interpolated from the relative distance to 
    # some of the determining points.
    # there is probably no point in doing a different interpolation than
    # linear. If that's too rough, it's probably a better idea
    # to increase the resolution of the grid, rather than smoothing
    # position values here.
    
    
    # the outcome should be that the points should get their
    
    triangle = find_relevant_triangle(point,cell)
    
    dist_sum = 0
    for x in triangle:
        dist_sum += x[0]
    
    # wait, this is wrong, I want the inverse. the further that
    # it is away, the less influece it should have.
    
    final_elevation = 0
    for x in triangle:
        final_elevation += (1-x[0]/dist_sum)*x[1][2]
    return final_elevation
    

def bary_centric_interpolation(P,tp1,tp2,tp3):
    """
    takes, "P" the point,
    tp1,tp2,tp3 are the triangle points
    https://codeplea.com/triangular-interpolation
    https://stackoverflow.com/questions/8697521/interpolation-of-a-triangle
    """
    
    # theoretically this could be done in parallel
    y_diff_1_3 = (tp1[1]-tp3[1])
    y_diff_2_3 = (tp2[1]-tp3[1])
    y_diff_3_1 = (tp3[1]-tp1[1])
    y_diff_p_3 = (P[1]-tp3[1])
    
    x_diff_1_3 = (tp1[0]-tp3[0])
    x_diff_3_2 = (tp3[0]-tp2[0])
    x_diff_p_3 = (P[0]-tp3[0])
    
    # ...then this
    first_product = y_diff_2_3 * x_diff_p_3
    second_product = x_diff_3_2 * y_diff_2_3
    third_product = y_diff_2_3 * x_diff_1_3
    forth_product = x_diff_3_2 * y_diff_1_3
    fifth_product = (y_diff_3_1 * x_diff_p_3)
    sixth_product = (x_diff_1_3 * y_diff_p_3)
    
    #...then this
    lower = (third_product + forth_product)
    
    # then this
    W_1 = (first_product + second_product) / lower
    W_2 = (fifth_product + sixth_product) / lower
    # then this
    W_3 = 1-W_1-W_2
    
    # I'm using it here for the z value, but the same weights can
    # be applied to any value you can make to the points
    # e.g. the delauney triangulation of my voronoi map
    value = W_1*tp1[2] + W_2*tp2[2] + W_3*tp3[2]
    
    return value
    

def find_relevant_triangle(point,cell):
    """this is assuming 2d cell
    
    it's finding which "fan blade" of my triangle fan, with center
    vertex is the appropriate one, to interpolate the z elevation
    from the values of the points or the center.
    """
    
    
    point=vector.Vector(point[0],point[1],0)
    dists=[]
    center2d=vector.Vector(0,0,0)
    center=vector.Vector(0,0,0)
    for x in cell:
        cell_vert = vector.Vector(*x)
        point2 = vector.Vector(x[0],x[1],0)
        d = point2 - point
        d = d.magnitude()
        dists.append( (d,cell_vert) )
        center2d += point2
        center += cell_vert
    center2d = center2d/len(cell)
    center = center/len(cell)
    
    dists.sort()
    #print(dists)
    #input()
    
    d = center-point
    d = d.magnitude()
    center_tup = (d,center)
    return dists[0],dists[1],center_tup
        
        
    a = 1
    

class MyEditor:
    def __init__(self,b):
        # this is necessary because the creator needs to get access
        # to show base to create new objects.
        self.b = b
        self.b.disableMouse()
        
        if not self.b.win.getGsg().getSupportsBasicShaders():
            self.t = addTitle(
                "Shadow Demo: Video driver reports that shaders are not supported.")
            return
        if not self.b.win.getGsg().getSupportsDepthTexture():
            self.t = addTitle(
                "Shadow Demo: Video driver reports that depth textures are not supported.")
            return
        
        
        
        # this is part of this editor
        self.engine_ob_counter = 0
        self.engine_obs = {}
        self.notes = []
        self.UI_elements = [] # like buttons, not the 3d markers
        self.new_obs = {}
        self.markers = []
        self.marker_objects = []
        self.engine_obs_pos = {}
        self.marker_texts = []
        self.my_positions = []
        
        self.build_buttons()
        self.camera_setup() # hmmmmm how to do this.
        self.cam_pos = vector.Vector(0,0,1)
        self.wasd_speed = 0.1
        #self.init_mouse_2d=
        self.init_box_draw_vars()
        self.placed = False
        self.marker_counter =0
        
        
        self.light = self.b.render.attachNewNode(Spotlight("Spot"))
        self.light.node().setScene(self.b.render)
        #self.light.node().setShadowCaster(True)
        self.light.node().showFrustum()
        self.light.node().getLens().setFov(40)
        self.light.node().getLens().setNearFar(10, 100)
        
        
        state = self.light.node().get_initial_state()
        state = state.remove_attrib(CullFaceAttrib)
        state = state.add_attrib(DepthOffsetAttrib.make(-3))
        self.light.node().set_initial_state(state)
        
        self.b.render.setLight(self.light)
        self.light.setPos(5,5,20)
        self.light.setHpr(0,-90,0)
        self.alight = self.b.render.attachNewNode(AmbientLight("Ambient"))
        self.alight.node().setColor(LVector4(0.2, 0.2, 0.2, 1))
        self.b.render.setLight(self.alight)
        
        # Important! Enable the shader generator.
        self.b.render.setShaderAuto()
        
        self.load_saved_river()
    
    def recursive_river_tree_unpack(self,my_dict):
        
        my_tuple_list = []
        for x in my_dict:
            if my_dict[x]!=None:
                lower_list = self.recursive_river_tree_unpack(my_dict[x])
                other_keys = list(my_dict[x].keys())
                for x2 in other_keys:
                    my_tuple_list.append((x,x2))
                    my_tuple_list.append((x2,x))
                my_tuple_list += lower_list
                
        return my_tuple_list
        
    def load_saved_river(self):
        d = sxml_main.read("saved_rivers.xml")
        d = d["data"]
        trees = d.pop("rivertrees")
        colormap = matplotlib.colormaps['terrain']
        
        my_river_tuple_list = self.recursive_river_tree_unpack(trees)
        my_river_tuple_list = list(set(my_river_tuple_list))
        
        
        
        all_verts = []
        vert_to_cell = {}
        for x in d:
            verts = d[x]["points"]
            for vert in verts:
                if vert not in vert_to_cell:
                    vert_to_cell[vert]=[]
                if x not in vert_to_cell[vert]:
                    vert_to_cell[vert].append(x)
            all_verts += verts
        all_verts = list(set(all_verts))
        
        # figure out elevation and spawn basic surfaces
        for x in d:
            
            # I should decide here if I'm creating a flat point
            
            my_center = vector.Vector(0,0,0)
            
            org_verts = d[x]["points"]
            new_verts = []
            for vert in org_verts:
                my_center += vector.Vector(*vert)
                z=0
                for cell in vert_to_cell[vert]:
                    z += d[cell]["elevation"]
                z = z / len(vert_to_cell[vert])
                new_vert = vector.Vector(*vert[:2],z)
                new_verts.append(new_vert)
            verts = new_verts
            my_center = my_center / len(org_verts)
            # no, I need these values anyway.
            
            
            # ok this doesn't exactly work, I need
            
            flat = True
            my_edge_list = []
            if d[x]["river value"]>1:
                flat = False
                my_edge_list = []
                for n in d[x]["neighbors"]:
                    if (x,n) not in my_river_tuple_list:
                        continue
                    edge_tuple = d[x]["neighbors"][n]
                    print(d[x]["neighbors"])
                    print("confirm, this is edge tuple",edge_tuple)
                    neighbor_value = d[n]["river value"]
                    if neighbor_value >1:
                        my_edge_list+=[list(edge_tuple[0])]
            #flat=True
            if flat:
                faces = [list(range(len(verts)))]
                new_ob = panda_object_create_load.make_object(self.b, verts, faces, twosided=True)
                el=d[x]["elevation"]
                color=colormap(el)
                new_ob.setColor(color)
                #new_ob.setPos(*vector.Vector(0,0,el))
                #new_object.setScale(1,1,0.1)
                #self.placed=True
            else:
                if True:
                    faces = [list(range(len(verts)))]
                    new_ob = panda_object_create_load.make_object(self.b, verts, faces, twosided=True)
                    el=d[x]["elevation"]
                    #color=colormap(el)
                    new_ob.setColor((0.7,0.7,0.95,0.8))
                    new_ob.setPos(0,0,-0.1)
                # this is skipping the "last vertex" when creating 
                # faces.
                
                r =  house.make(verts,my_edge_list,"world","river_short_absolute",cap_ends=False)
                house_verts, faces = r 
                new_house_verts = []
                
                #my_center = d[x]["center"]
                if False:
                    for vert in house_verts:
                        
                        # this is kind of useless, it fetches the first one correctly, but that's it.
                        my_triangle = find_relevant_triangle(vert,verts)
                        
                        other = my_triangle[0][1]
                        
                        if False:
                            newz = 0
                            dist_sum = 0
                            print(other)
                            other  = tuple((other[0],other[1],0))
                            for neighbor in vert_to_cell[other]:
                                neighborverts = d[neighbor ]["points"]
                                that_cell_center = vector.Vector(0,0,0)
                                for vert in neighborverts:
                                    that_cell_center += vector.Vector(*vert)
                                that_cell_center = that_cell_center / len(neighborverts )
                                dx = that_cell_center - other
                                dist_x = dx.magnitude()
                                dist_sum += dist_x
                                newz +=  d[neighbor]["elevation"] * dist_x
                            newz = newz/dist_sum
                            
                            z = newz
                        
                        if False:
                            other = vector.Vector(*other)
                            dvec1 = my_center - vector.Vector(*vert)
                            dvec2 = other  - vector.Vector(*vert)
                            
                            dist1 = dvec1.magnitude()
                            dist2 = dvec2.magnitude()
                            
                            full_dist = dist1 + dist2
                            
                            z = round(dist1/full_dist,0) * d[x]["elevation"] + round(dist2/full_dist,0) * other[2]
                            
                        old_z = float(vert[2])
                        
                        if True:
                            z = bary_centric_interpolation(vert,my_triangle[0][1],my_triangle[1][1],my_triangle[2][1])
                        new_house_vert = vector.Vector(vert[0],vert[1],z+old_z)#
                        new_house_verts.append(new_house_vert)
                        
                        house_verts = new_house_verts
                new_ob = panda_object_create_load.make_object(self.b, house_verts, faces, twosided=False)
                el=d[x]["elevation"]
                color=colormap(el)
                new_ob.setColor(color)
                #new_ob.setPos(*vector.Vector(0,0,el))
                # figure out where my connections to other cells are
                # mostly via
                # "what's my score, what's their score."
                # "if score" > 5
                # mark the connection.
                # this actually highlights that I probably need
                # a different set of keypoints, depending on the 
                # exit of the thing.
                a=1
            
            
        
    def init_box_draw_vars(self):
        self.first_point3d=None
        self.second_point3d=None
        self.first_point=None
        self.my_box=[]
        self.heading_scaling = 100
        self.x_mouse_diff_2d = None
        
    def get_2d_position(self,pos_3d_tuple):
        pos2d=Point3()
        
        verts=[]
        faces=[]
        
        #bitmask=BitMask32.bit(1)
        fake=panda_object_create_load.make_object(self.b,verts,faces)
        
        fake.setPos(pos_3d_tuple)
        gcp=fake.getPos(self.b.cam)
        inViewpos =self.b.camLens.project(gcp,pos2d)
        fake.removeNode()
        
        return pos2d
    
    def set_x_mouse_diff_2d(self,input_d):
        mouse_3d = input_d["mouse 3d"]
        if mouse_3d != None and self.b.mouseWatcherNode.is_button_down("mouse1"):
            if self.first_point == None:
                self.first_point = self.get_2d_position(mouse_3d)
                self.first_point3d = mouse_3d
            
            self.second_point3d = mouse_3d
            second_point = self.get_2d_position(mouse_3d)
            fp = self.first_point
            sp = second_point
            
            self.x_mouse_diff_2d = fp[0]-sp[0]
        else:
            self.old_hpr = self.cam.getHpr()
            self.first_point = None
            self.x_mouse_diff_2d = None
    
    def cam_rot_update(self):
        h,p,r = self.cam.getHpr()
        old_h,old_p,old_r=self.old_hpr
        if self.x_mouse_diff_2d!=None: 
            # this works, but I don't want it turned on right now.
            M = vector.RotationMatrix(h/360*2*math.pi,vector.Vector(0,0,1))
            h = self.x_mouse_diff_2d*self.heading_scaling
            self.cam.setHpr(h+old_h,p,r)
            #self.dvec=M*self.dvecbase*self.zoom
            
    def camera_setup(self):
        # should be fine, don't move yet.
        self.b.disableMouse()
        self.cam = self.b.camera
        #like focal point
        self.anchor_point = vector.Vector(0,0,0)
        self.anchor_object = None
        self.notmovedfor   = 0
        self.lastanchorpos = vector.Vector(0,0,0)
        self.cam.setPos(0,-10,5)
        self.cam.setHpr(0,-25,0)
    
    def build_buttons(self):
        b1 = pig.create_custom_button("save markers",(-0.4,0,-0.9),self.save,[])
        b2 = pig.create_custom_button("load",(-0.0,0,-0.9),self.load,[])
        b3 = pig.create_custom_button("load terrain",(0.2,0,-0.9),self.load,[])
        b1.setScale(0.05)
        b2.setScale(0.05)
        b3.setScale(0.05)
    
    def load_terrain(self):
        with open("myterrain.csv","r") as f:
            t = f.read()
        
        for line in t.readlines():
            line = line.split(";")
            
            
        
    def save(self,*args):
        
        sxml_main.write("my_save.xml",{"this":self.markers})
        self.placed = True
        
    def load(self,*args):
        if self.marker_objects == []:
            my_dict = sxml_main.read("my_save.xml")
            for marker in my_dict["this"]:
                
                self.make_UI_marker(*marker)
                self.placed = False
        self.placed = True
        
    def make_UI_marker(self,pos,text=None):
        if self.placed == False:
            if False:
                if text == None:
                    text = "marker"+str(self.marker_counter)
                self.markers.append((tuple(pos),text))
                text_node = pig.create_textline(text,pos)
                text_node.reparentTo(self.b.render)
                text_node.setPos(pos)
                text_node.setScale(1)
                self.placed = True
                self.marker_counter += 1
                self.marker_objects.append(text_node)
                
            
            points = [
            vector.Vector(1,0,0.1),
            vector.Vector(1,1,0.1),
            vector.Vector(0,1,0.1),
            vector.Vector(0,0,0.1),
            ]
            
            # ok, so right now I'm generating points very nicely. except I'm doing it 
            # for the edge things that I don't want to see between the tiles.
            
            #randomize how many and whiches ones I'm skipping.
            
            m = random.choice([1,2,3,4])
            my_choices=[]
            c=0
            while c < m:
                this=random.choice([[0,1],[1,2],[2,3],[3,0]])
                if this in my_choices:
                    continue
                my_choices.append(this)
                c+=1
                
            my_choices.sort()
            
            #r =  house.make(points,[[0,1],[3,0]],"world","river",cap_ends=False)
            r =  house.make(points,my_choices,"world","river",cap_ends=False)
            #r =  house.make(points,[],"world","river",cap_ends=False)
            
            tex = loader.loadTexture("colorgrid.png")
            verts, faces = r 
            
            #new_object = panda_object_create_load.make_object(self.b, points, twosided=True,texture=tex)
            new_object = panda_object_create_load.make_object(self.b, verts, faces, twosided=False)
            new_object.setPos(*vector.Vector(*pos)+vector.Vector(0,0,0.5))
            #new_object.setScale(1,1,0.1)
            self.placed=True
            #new_object.node().setTexture(tex)
            #new_object.node().set_shadow_caster(True)
            #self.b.cam.lookAt(*pos)
            #self.light.lookAt(*pos)
            if False:    
                for caster in self.get_all_casters():
                    if isinstance(caster, p3d.PointLight):
                        logging.warning(
                            f'PointLight shadow casters are not supported, disabling {caster.name}'
                        )
                        caster.set_shadow_caster(False)
                        recompile = True
                        continue
                    state = caster.get_initial_state()
                    if not state.has_attrib(p3d.ShaderAttrib):
                        attr = self._create_shadow_shader_attrib()
                        state = state.add_attrib(attr, 1)
                        state = state.remove_attrib(p3d.CullFaceAttrib)
                        caster.set_initial_state(state)

            
    def make_new_squares(self,mypos):
        self.engine_ob_counter+=1
        #color = (random.random(),random.random(),0,)
        pos = vector.Vector(*mypos)
        verts = [
        vector.Vector(pos[0],  pos[1]  ,pos[2]),
        vector.Vector(pos[0]+1,pos[1]  ,pos[2]),
        vector.Vector(pos[0]+1,pos[1]+1,pos[2]),
        vector.Vector(pos[0],  pos[1]+1,pos[2]),
        ]
        faces = [[0,1,2,3]]
        
        Wo = WorldObject(self.engine_ob_counter)
        Wo.verts = verts
        
        engine_ob = panda_object_create_load.make_object(self.b, verts, faces, twosided=False)
        
        self.engine_obs[self.engine_ob_counter] = engine_ob
        self.engine_obs_pos[str(mypos)] = engine_ob
        Wo.pos = vector.Vector(0,0,0) # it's a bit annoying, but apparently you can either set vert position or this position. so.
        self.new_obs[self.engine_ob_counter] = [Wo,"terrain"]
    
    def main(self,inputs,*args):
        if False:
            if len(inputs) == 3:
                mouse_pos, col_tags, hardwareinputs = inputs
                self.ensure_squares(mouse_pos)
                if self.b.mouseWatcherNode.is_button_down("mouse1"):
                    self.make_UI_marker(mouse_pos,"hello test")
            if not self.b.mouseWatcherNode.is_button_down("mouse1"):
                self.placed = False
                
            if len(inputs)>0:
                in_d={"mouse 3d":inputs[0]}
                self.set_x_mouse_diff_2d(in_d)
                self.cam_rot_update()
        self.wasd_movement()
        
    def wasd_movement(self):
        
        l = [(0,1,0),(-1,0,0),(0,-1,0),(1,0,0)]
        l = [vector.Vector(*x) for x in l]
        c = 0
        pos = vector.Vector(*self.cam.getPos())
        keys = ["w","a","s","d"]
        while c < 4:
            key = keys[c]
            vec = l[c]
            if self.b.mouseWatcherNode.is_button_down(key):
                pos += vec*self.wasd_speed
            c+=1
        self.cam.setPos(tuple(pos))
        
    def ensure_squares(self,mouse_pos=None):
        # make new squares
        # initialze if empty
        return
        if len(self.engine_obs_pos)==0 or mouse_pos==None:
            mouse_pos=vector.Vector(0,0,0)
        x = round(mouse_pos[0],0)
        y = round(mouse_pos[1],0)
        
        yw = 7 # adjust to taste.
        xw = 7
        cx = 0
        
        xoffset=int.__floordiv__(xw,2)
        yoffset=int.__floordiv__(yw,2)

        # that' probably relatively expensive to test, I can 
        # there are easier ways to do this...
        while cx < xw:
            cy = 0
            while cy < yw:
                pos = (x -xoffset +cx,y-yoffset+cy,0)
                
                if str(pos) not in self.engine_obs_pos:
                    self.make_new_squares(pos)
                    self.my_positions.append(str(pos))
                cy += 1
            cx += 1 
        
        
        
class Wrapper:
    def __init__(self):
        self.b = ShowBase()
        props = WindowProperties( )
        props.setTitle('3d editor')
        self.b.win.requestProperties( props )
        self.editor = MyEditor(self.b)
        self.collisions = panda_collisions.CollisionWrapper()
        self.collisions.setup_mouse_ray()
        self.event_handler = DirectObject.DirectObject()
        self.inputs = [] # this is where remapped keyboad and mouse input goes to.
        #self.event_handler.accept("mouse1-repeat",self.pass_on,["left mouse held"])
        #self.event_handler.accept("mouse3-repeat",self.pass_on,["right mouse held"])
        #self.event_handler.accept("a-repeat",self.pass_on,["a held"])
        #self.event_handler.accept("a",self.pass_on,["a"])
        #self.event_handler.accept("mouse1",self.pass_on,["left mouse"])
        
        self.buttons_move_actions = {"mouse1":"left mouse",
                        "mouse3":"right mouse",
                        "a":"a"}
        
        self.create_move_task()
        
        
        
    def pass_on(self,action):
        if action not in self.inputs:
            self.inputs.append(action)
            
    def create_move_task(self):
        self.b.taskMgr.add(move_task,"Move Task",extraArgs=[self],appendTask=True)
        
def move_task(*args):
    #somewhat selfexplanatory? It's the watcher thing that
    #tracks movement inputs
    
    Task=args[1]
    wrapper=args[0]
    is_down = wrapper.b.mouseWatcherNode.is_button_down
    
    for mb in wrapper.buttons_move_actions:
        if is_down(mb):
            wrapper.pass_on(wrapper.buttons_move_actions[mb])
                
    return Task.cont
    
def main():
    W = Wrapper()
    inputs = []
    while True:
        inputs += [W.inputs]
        W.inputs=[]
        W.b.taskMgr.step()
        W.editor.main(inputs)
        inputs = []
        #W.collisions.update({"create complex":W.editor.new_obs})
        W.editor.new_obs = {}
        if W.b.mouseWatcherNode.hasMouse():
            mpos = W.b.mouseWatcherNode.getMouse() 
            campos = W.editor.cam.getPos()
            camhpr = W.editor.cam.getHpr()
            mouse_data = ((W.b.camNode,mpos.getX(),mpos.getY()),campos,camhpr)
            
            pos,tags = W.collisions.mouse_ray_check(mouse_data)
            inputs += [pos,tags]
        
if __name__ == "__main__":
    main()
