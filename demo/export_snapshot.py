"""Export only aggregated, verified study results for the standalone local demo."""
from pathlib import Path
import argparse,gzip,hashlib,json
from datetime import datetime,timezone
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import box,mapping
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
DATA_DIR=Path(__file__).resolve().parent/'data'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def export_snapshot(model_run=None):
    if model_run is None:
        pointer=ROOT/'outputs/region_modeling/latest_run.json'
        if not pointer.is_file():raise FileNotFoundError('Missing completed modeling outputs. Run the modeling notebook first or use the included demo/data snapshot.')
        run=Path(json.loads(pointer.read_text(encoding='utf-8'))['folder'])
    else:run=Path(model_run).resolve()
    read=lambda name:json.loads((run/name).read_text(encoding='utf-8'))
    verified=read('independent_verification.json')
    if verified['status']!='passed':raise ValueError('Only verified model outputs may be exported.')
    cfg=read('config.json');spec=read('selected_spec.json')
    source=ROOT/cfg['train_run'];source_cfg=json.loads((source/'config.json').read_text(encoding='utf-8'))
    baseline=ROOT/source_cfg['baseline_run']
    edges=gpd.read_parquet(baseline/'edges.parquet')
    edges=edges[edges.length_inside_m>1e-8].sort_values('edge_id').reset_index(drop=True)
    edges['edge_index']=np.arange(len(edges),dtype=np.uint16)
    project=Transformer.from_crs(4326,cfg['metric_crs'],always_xy=True)
    region=shapely.transform(box(*cfg['bbox']),project.transform,interleaved=False)
    geometries=shapely.simplify(shapely.intersection(edges.geometry.to_numpy(),region),2.,preserve_topology=True)
    backward=Transformer.from_crs(cfg['metric_crs'],4326,always_xy=True)
    geometries=shapely.transform(geometries,backward.transform,interleaved=False)
    features=[{'type':'Feature','id':int(index),'properties':{'i':int(index)},'geometry':mapping(geometry)}
              for index,geometry in enumerate(geometries)]
    fields=['edge_id','day_group','slot','estimated_speed_kmh','reference_speed_kmh','speed_ratio','n_trips','n_taxis','n_days',
        'eligible_days','slow_days','slow_frequency','status','is_recurrent','prediction_source','predicted_speed_kmh']
    profiles=pd.read_parquet(run/'edge_time_profiles_for_future_demo.parquet',columns=fields)
    lookup=edges.set_index('edge_id').edge_index
    profiles['edge_index']=profiles.edge_id.map(lookup).astype('uint16');profiles=profiles.drop(columns='edge_id')
    for name in ['day_group','status','prediction_source']:profiles[name]=profiles[name].astype('category')
    profiles['slot']=profiles.slot.astype('uint8')
    for name in ['n_trips','n_taxis','n_days','eligible_days','slow_days']:
        profiles[name]=profiles[name].fillna(0).astype('uint32' if name=='n_trips' else 'uint16')
    for name in ['estimated_speed_kmh','reference_speed_kmh','speed_ratio','slow_frequency','predicted_speed_kmh']:
        profiles[name]=profiles[name].astype('float32')
    clusters=pd.read_parquet(run/'historical_recurrent_clusters.parquet').copy()
    clusters['edge_indices']=clusters.edge_ids.map(lambda values:[int(lookup.loc[e]) for e in values])
    clusters=clusters.drop(columns=['edge_ids','graph_hash'])
    index=edges[['edge_index','edge_id','road_class','length_inside_m']].copy()
    forbidden={'trip_id','taxi_id','polyline','timestamp'}
    assert not forbidden & {str(c).lower() for c in profiles.columns}
    assert len(profiles)==len(edges)*(24//spec['width'])*(7 if spec['day_group']=='weekday' else 2)
    assert profiles[['edge_index','day_group','slot']].duplicated().sum()==0
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(DATA_DIR/'network.geojson.gz'),mode='wb',mtime=0) as handle:
        handle.write(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,separators=(',',':')).encode())
    for name,frame in [('edges',index),('profiles',profiles),('recurrent_clusters',clusters)]:
        frame.to_parquet(DATA_DIR/f'{name}.parquet',index=False,compression='zstd')
    metrics=pd.read_parquet(run/'eta_metrics.parquet').query('group == "all"').to_dict('records')
    files=['network.geojson.gz','edges.parquet','profiles.parquet','recurrent_clusters.parquet']
    metadata={'schema_version':1,'source_run':run.name,'graph_hash':spec['graph_hash'],
        'generated_utc':datetime.now(timezone.utc).isoformat(),'region':'C 8×8 km · Porto','bbox':cfg['bbox'],
        'timezone':cfg['timezone'],'train_start':cfg['train_start'],'train_end_exclusive':cfg['train_end'],
        'hour_width':spec['width'],'day_grouping':spec['day_group'],'slowdown_ratio_threshold':spec['slowdown_threshold'],
        'min_trips':spec['min_trips'],'min_taxis':cfg['min_taxis'],'min_days':cfg['min_days'],
        'min_recurrent_frequency':cfg['min_recurrent_frequency'],'n_edges':len(edges),'n_profile_rows':len(profiles),
        'geometry_simplification_m':2.,'metrics':metrics,'evaluation_coverage':read('evaluation_coverage.json'),
        'source_verification_checks':verified['n_checks'],
        'scope':'Aggregated train GPS taxi slowdown patterns; no raw GPS or trip/taxi IDs; no independent congestion labels.',
        'dataset_url':'https://www.kaggle.com/competitions/pkdd-15-predict-taxi-service-trajectory-i/data',
        'map_attribution':'Map data © OpenStreetMap contributors (ODbL).',
        'files':{name:{'sha256':digest(DATA_DIR/name),'bytes':(DATA_DIR/name).stat().st_size} for name in files}}
    (DATA_DIR/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'exported':str(DATA_DIR),'edges':len(edges),'profiles':len(profiles),
        'total_mib':round(sum(p.stat().st_size for p in DATA_DIR.iterdir() if p.is_file())/2**20,2)},ensure_ascii=False,indent=2))
    return metadata

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model-run')
    export_snapshot(parser.parse_args().model_run)
