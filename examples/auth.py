from ritz import ritz, parse_tcl_config
import argparse



def main():
  parser = argparse.ArgumentParser(description='Process some integers.')

  parser.add_argument('--prod', action='store_true')
  parser.add_argument('--remove-all-pms', action='store_true')

  args = parser.parse_args()
  conf = parse_tcl_config("~/.ritz.tcl")

  if args.prod:
    c_server = conf["default"]["Server"]
    c_user   = conf["default"]["User"]
    c_secret = conf["default"]["Secret"]
  else:
    c_server = conf["UNINETT-backup"]["Server"]
    c_user   = conf["UNINETT-backup"]["User"]
    c_secret = conf["UNINETT-backup"]["Secret"]
  sess = ritz(c_server)
  sess.connect()
  sess.authenticate(c_user, c_secret)

  return sess


  return






if __name__ == "__main__":
  s = main()
