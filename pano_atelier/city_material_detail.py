"""Mineral concrete refinement: restrained rain, local repairs, fine formwork joints."""
import bpy
from .station_procedural import node,feed,noise,mapped,mix,math as smath

def refine(mat):
    if mat.get('pa_mineral_refinement') or not mat.node_tree:return False
    t=mat.node_tree
    if not t.nodes.get('Ruissellement vertical'):return False
    t.nodes['Ruissellement vertical'].inputs[1].default_value=(3.8,3.8,.42)
    t.nodes['Patine · pluie'].inputs['To Max'].default_value=.14
    co=t.nodes['Origine du grain'].outputs[0];base=t.nodes['Beton · creux'].outputs[0]
    destinations=[l.to_socket for l in list(base.links)]
    patch=mapped(t,'Reprises · masque mineral',noise(t,'Reprises · ciment heterogene',co,1.25,4),.48,.76,0,.16)
    color=mix(t,'Reprises · variation localisee',patch,base,(.13,.15,.12,1))
    # Object-space vertical panel joints, suppressed on horizontal faces.
    tc=t.nodes['Coordonnees locales en metres'];sep=node(t,'ShaderNodeSeparateXYZ','Coffrage · position');feed(t,sep.inputs[0],tc.outputs['Object'])
    g=node(t,'ShaderNodeNewGeometry','Coffrage · geometrie');tr=node(t,'ShaderNodeVectorTransform','Coffrage · normale locale');tr.vector_type='NORMAL';tr.convert_from='WORLD';tr.convert_to='OBJECT';feed(t,tr.inputs[0],g.outputs['Normal']);ns=node(t,'ShaderNodeSeparateXYZ','Coffrage · axes normaux');feed(t,ns.inputs[0],tr.outputs[0])
    side=smath(t,'ABSOLUTE',ns.outputs['X']);u=smath(t,'ADD',smath(t,'MULTIPLY',sep.outputs['X'],smath(t,'SUBTRACT',1,side)),smath(t,'MULTIPLY',sep.outputs['Y'],side))
    seams=[]
    for value,pitch in ((u,2.4),(sep.outputs['Z'],1.8)):
        f=smath(t,'FRACT',smath(t,'DIVIDE',value,pitch));dist=smath(t,'MINIMUM',f,smath(t,'SUBTRACT',1,f));seams.append(smath(t,'LESS_THAN',dist,.003))
    seam=smath(t,'MULTIPLY',smath(t,'MAXIMUM',seams[0],seams[1]),smath(t,'SUBTRACT',1,smath(t,'ABSOLUTE',ns.outputs['Z'])))
    result=mix(t,'Coffrage · joint fin',smath(t,'MULTIPLY',seam,.20),color,(.09,.10,.08,1))
    for s in destinations:feed(t,s,result)
    bs=t.nodes.get('Principled BSDF');previous=bs.inputs['Normal'].links[0].from_socket
    bump=node(t,'ShaderNodeBump','Coffrage · leger creux');bump.inputs['Distance'].default_value=.0015;bump.inputs['Strength'].default_value=.28;feed(t,bump.inputs['Normal'],previous);feed(t,bump.inputs['Height'],smath(t,'SUBTRACT',1,seam));feed(t,bs.inputs['Normal'],bump.outputs[0])
    mat['pa_mineral_refinement']=True;return True
