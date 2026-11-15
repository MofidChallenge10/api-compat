#!/usr/bin/env python3
"""Report likely breaking changes between two OpenAPI 3 JSON documents."""
import argparse,json,sys,unittest
METHODS={"get","post","put","patch","delete","options","head","trace"}
def operation_map(doc):
    return {p:{m:o for m,o in item.items() if m in METHODS and isinstance(o,dict)}
            for p,item in doc.get("paths",{}).items() if isinstance(item,dict)}
def compare(old,new):
    issues=[]; before=operation_map(old); after=operation_map(new)
    for path,methods in before.items():
        if path not in after: issues.append(f"BREAKING removed path {path}"); continue
        for method,op in methods.items():
            if method not in after[path]: issues.append(f"BREAKING removed operation {method.upper()} {path}"); continue
            newer=after[path][method]
            oldp={(p.get("in"),p.get("name")):p for p in op.get("parameters",[]) if isinstance(p,dict)}
            newp={(p.get("in"),p.get("name")):p for p in newer.get("parameters",[]) if isinstance(p,dict)}
            for key in oldp.keys()-newp.keys(): issues.append(f"BREAKING removed parameter {key[0]}:{key[1]} from {method.upper()} {path}")
            for key,p in newp.items():
                if p.get("required") and not oldp.get(key,{}).get("required"): issues.append(f"BREAKING newly required parameter {key[0]}:{key[1]} on {method.upper()} {path}")
            if newer.get("requestBody",{}).get("required") and not op.get("requestBody",{}).get("required"): issues.append(f"BREAKING request body became required on {method.upper()} {path}")
            for status,response in op.get("responses",{}).items():
                neweresp=newer.get("responses",{}).get(status)
                if not neweresp: continue
                oldschema=response.get("content",{}).get("application/json",{}).get("schema",{})
                newschema=neweresp.get("content",{}).get("application/json",{}).get("schema",{})
                for prop in oldschema.get("properties",{}).keys()-newschema.get("properties",{}).keys(): issues.append(f"BREAKING removed response property {prop} ({status}) from {method.upper()} {path}")
                for prop in set(newschema.get("required",[]))-set(oldschema.get("required",[])): issues.append(f"BREAKING response property became required: {prop} ({status}) on {method.upper()} {path}")
    return sorted(set(issues))
class Tests(unittest.TestCase):
    def test_removed_path(self): self.assertTrue(any("removed path" in x for x in compare({"paths":{"/a":{"get":{}}}},{"paths":{}})))
    def test_required_parameter(self):
        a={"paths":{"/a":{"get":{"parameters":[]}}}}; b={"paths":{"/a":{"get":{"parameters":[{"in":"query","name":"q","required":True}]}}}}
        self.assertTrue(any("newly required" in x for x in compare(a,b)))
    def test_same(self): self.assertEqual(compare({"paths":{}},{"paths":{}}),[])
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("old"); ap.add_argument("new"); a=ap.parse_args()
    try:
        with open(a.old,encoding="utf-8") as f: old=json.load(f)
        with open(a.new,encoding="utf-8") as f: new=json.load(f)
    except (OSError,json.JSONDecodeError) as exc: ap.error(str(exc))
    issues=compare(old,new); print("\n".join(issues) if issues else "No breaking changes found by supported checks."); raise SystemExit(bool(issues))
if __name__=="__main__":
    if "--self-test" in sys.argv: unittest.main(argv=[sys.argv[0]])
    else: main()
